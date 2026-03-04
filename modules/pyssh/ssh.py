"""gridとのファイル送受信、ジョブ実行を行う"""

import glob
import io
import json
import os
import stat
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, fields
from typing import IO, Any

import paramiko

from config import load_ssh_config, throw_yaml_nonexistent_error


def print_stdout(stdout):
    for line in stdout:
        if line:
            print(line, end="")


@dataclass
class SSH_SETTING:
    host: str | None = None
    port: str | None = None
    user: str | None = None
    password: str | None = None
    windows_local_basedirpath: str | None = None
    linux_local_basedirpath: str | None = None
    remote_basedirpath: str | None = None

    _hostname: str | None = None

    def __post_init__(self):
        config = load_ssh_config(hostname=self._hostname)
        for f in fields(self):
            if f.name == "_hostname":
                continue
            setattr(self, f.name, getattr(config, f.name))
        self.validate()

    def validate(self):
        none_list = []
        for f in fields(self):
            if f.name in ["_hostname"]:
                continue
            if getattr(self, f.name) is None:
                none_list.append(f.name)
        if none_list:
            msg = "'" + ", ".join(none_list) + "' がNoneです。.pyssh.yaml定義を確認ください。"
            raise ValueError(msg)


def get_local_filepath_from_remote_filepath(remote_filepath: str) -> str:
    setting = SSH_SETTING()
    if setting.remote_basedirpath is None or setting.windows_local_basedirpath is None:
        raise throw_yaml_nonexistent_error(
            f"remote_basedirpath:{setting.remote_basedirpath}, windows_local_basedirpath:{setting.windows_local_basedirpath}"
        )

    local_filepath = remote_filepath.replace(setting.remote_basedirpath, setting.windows_local_basedirpath)
    return local_filepath


def get_local_linux_filepath(local_filepath: str) -> str:
    if is_windows_system():
        filepath = local_filepath.replace("\\", "/")
        filepath = "/mnt/" + filepath[0].lower() + filepath[2:]
        return filepath
    else:
        return local_filepath


def get_remote_filepath(local_filepath: str) -> str:
    setting = SSH_SETTING()
    if setting.remote_basedirpath is None or setting.linux_local_basedirpath is None:
        raise throw_yaml_nonexistent_error(
            f"remote_basedirpath:{setting.remote_basedirpath}, linux_local_basedirpath:{setting.linux_local_basedirpath}"
        )

    if "\\" in local_filepath:
        local_filepath = get_local_linux_filepath(local_filepath)
    remote_filepath = local_filepath.replace(setting.linux_local_basedirpath, setting.remote_basedirpath)
    return remote_filepath


def is_windows_system() -> bool:
    return "\\" in os.getcwd()


class SSHClient:
    def __init__(
        self,
        local_filepath_list: list[str],
        remote_filepath_list: list[str] | None = None,
        setting: SSH_SETTING = SSH_SETTING(),
    ):
        self.setting = setting

        if isinstance(local_filepath_list, str):
            local_filepath_list = [local_filepath_list]
        if remote_filepath_list is not None and len(local_filepath_list) != len(remote_filepath_list):
            raise ValueError(
                f"filepath_list size must be all same ({len(remote_filepath_list)} != {len(local_filepath_list)})"
            )

        new_local_filepath_list = []
        for i in local_filepath_list:
            if "*" in i:
                if "/" not in i and "\\" not in i:
                    i = "./" + i
                local_dirpath_i = get_remote_filepath(os.path.abspath(os.path.dirname(i)))
                remote_filepath_list_i = self.remote_ls(remote_dirpath=local_dirpath_i)
                remote_filepath_list_i = [
                    j for j in remote_filepath_list_i if os.path.basename(i).replace("*", "") in j
                ]
                local_filepath_list_i = [get_local_filepath_from_remote_filepath(j) for j in remote_filepath_list_i]
                new_local_filepath_list += local_filepath_list_i
            else:
                new_local_filepath_list.append(i)

        self._local_filepath_list = new_local_filepath_list
        self._remote_filepath_list = remote_filepath_list

    def __str__(self) -> str:
        text = ""
        for local_filepath, remote_filepath in self.iterate_filepath():
            text += local_filepath + " -> " + remote_filepath
        return text

    def __repr__(self) -> str:
        return str(self)

    def iterate_filepath(self) -> Iterator[tuple[str, str]]:
        yield from zip(self.local_filepath_list, self.remote_filepath_list, strict=False)

    @property
    def local_filepath_list(self) -> list[str]:
        return [os.path.abspath(i) for i in self._local_filepath_list]

    @property
    def remote_filepath_list(self) -> list[str]:
        if self._remote_filepath_list is None:
            return [get_remote_filepath(i) for i in self.local_filepath_list]
        else:
            return self._remote_filepath_list

    def get_remote_dirpath_list(self) -> list[str]:
        return [os.path.dirname(i) for i in self.remote_filepath_list]

    def make_remote_directories(self):
        remote_dirpath_list = list(set(self.get_remote_dirpath_list()))
        command = "mkdir -p " + " ".join(remote_dirpath_list)
        execute_command(command, setting=self.setting)
        time.sleep(0.1)

    def put(self):
        self.make_remote_directories()

        with get_sftp_connection(setting=self.setting) as sftp:
            for local_filepath, remote_filepath in self.iterate_filepath():
                try:
                    if os.path.isdir(local_filepath):
                        execute_command(f"mkdir -p {remote_filepath}", setting=self.setting)
                        time.sleep(0.1)
                        client = SSHClient(
                            local_filepath_list=glob.glob(local_filepath + "/*"),
                            setting=self.setting,
                        )
                        client.put()
                    else:
                        t1 = time.time()
                        sftp.put(localpath=local_filepath, remotepath=remote_filepath)
                        t2 = time.time()
                        print(f"put {local_filepath} (in {t2 - t1:.1f} sec.)")
                except Exception as e:
                    print(f"Faild to put {local_filepath} ({e})")
                    raise e

    def get(self, done: set | None = None):
        if done is None:
            done = set()
        with get_sftp_connection(setting=self.setting) as sftp:
            for local_filepath, remote_filepath in self.iterate_filepath():
                if local_filepath in done:
                    continue
                done.add(local_filepath)
                try:
                    if is_remote_directory(sftp, remote_filepath):
                        # os.system(f"mkdir -p {local_filepath}")
                        if not os.path.exists(local_filepath):
                            os.makedirs(local_filepath)
                        # print(self.remote_glob(local_filepath, return_local_filepath=True))
                        client = SSHClient(
                            # local_filepath_list=glob.glob(local_filepath + "/*"),
                            local_filepath_list=self.remote_glob(local_filepath, return_local_filepath=True),
                            setting=self.setting,
                        )
                        client.get(done)
                    else:
                        t1 = time.time()
                        sftp.get(remote_filepath, local_filepath)
                        t2 = time.time()
                        print(f"got {local_filepath} (in {t2 - t1:.1f} sec.)")
                except Exception as e:
                    print(f"Failed to get {remote_filepath} ({e})")
                    raise e

    def execute_command(
        self,
        command: str,
        # cd: bool = False,
        cd: bool = True,
        remote_dirpath: str | None = None,
        verbose: bool = True,
    ):
        return execute_command(
            command=command,
            cd=cd,
            remote_dirpath=remote_dirpath,
            verbose=verbose,
            setting=self.setting,
        )

    def execute_local_script_on_remote(self, script_dict: dict[str, str], remote_dirpath: str | None = None):
        org_local_filepath_list = self._local_filepath_list
        org_remote_filepath_list = self._remote_filepath_list
        local_filepath_list = list(script_dict.keys())
        self.__init__(local_filepath_list=local_filepath_list, setting=self.setting)
        self.put()
        remote_filepath_list = self.remote_filepath_list

        for remote_filepath_i, command_i in zip(remote_filepath_list, script_dict.values(), strict=False):
            self.execute_command(
                f"chmod +x {remote_filepath_i} && {command_i} && rm {remote_filepath_i}",
                remote_dirpath=remote_dirpath,
                cd=True,
            )

        self._local_filepath_list = org_local_filepath_list
        self._remote_filepath_list = org_remote_filepath_list

    def remote_ls(self, remote_dirpath: str | None = None) -> list[str]:
        if remote_dirpath is None:
            local_dirpath = os.getcwd()
            remote_dirpath = get_remote_filepath(local_dirpath)
        if not remote_dirpath.endswith("/"):
            remote_dirpath += "/"

        stdout = self.execute_command(f"ls {remote_dirpath}", verbose=False)
        filepath_list = stdout.split("\n")
        filepath_list = [remote_dirpath + i for i in filepath_list]
        return filepath_list

    def remote_glob(self, local_dirpath: str, return_local_filepath: bool = False):
        remote_dirpath = get_remote_filepath(local_dirpath)
        remote_filepath_list = self.remote_ls(remote_dirpath + "/")
        if return_local_filepath:
            local_filepath_list = [get_local_filepath_from_remote_filepath(i) for i in remote_filepath_list]
            return local_filepath_list
        else:
            return remote_filepath_list


@contextmanager
def get_ssh_client(
    setting: SSH_SETTING = SSH_SETTING(),
) -> Iterator[paramiko.SSHClient]:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    if setting.host is None or setting.port is None:
        raise throw_yaml_nonexistent_error(f"host:{setting.host}, port:{setting.port}")
    client.connect(
        setting.host,
        port=int(setting.port),
        username=setting.user,
        password=setting.password,
    )
    msg = f"connecting to {setting.host}"
    if setting._hostname:
        msg += f" ({setting._hostname})"
    print(msg)
    try:
        yield client
    finally:
        client.close()


@contextmanager
def get_sftp_connection(
    setting: SSH_SETTING = SSH_SETTING(),
) -> Iterator[paramiko.SFTPClient]:
    with get_ssh_client(setting) as client:
        try:
            sftp = client.open_sftp()
            yield sftp
        finally:
            sftp.close()


def is_remote_directory(sftp: paramiko.SFTPClient, path: str) -> bool | None:
    try:
        mode = sftp.stat(path).st_mode
        if mode is None:
            raise ValueError
        return stat.S_ISDIR(mode)
    except FileNotFoundError:
        return None


def execute_command(
    command: str,
    # cd: bool = False,
    cd: bool = True,
    remote_dirpath: str | None = None,
    verbose: bool = True,
    setting: SSH_SETTING = SSH_SETTING(),
):
    if remote_dirpath is None:
        local_dirpath = os.getcwd()
        remote_dirpath = get_remote_filepath(local_dirpath)

    if cd:
        command = f"cd {remote_dirpath} && {command}"

    if verbose:
        print(command)

    with get_ssh_client(setting=setting) as client:
        stdin, stdout, stderr = client.exec_command(f"mkdir -p {remote_dirpath}")

        stdin, stdout, stderr = client.exec_command(command)
        stdout = stdout.read().decode("utf-8")
        stderr = stderr.read().decode("utf-8")
        if verbose:
            print_stdout(stdout)
            print_stdout(stderr)
        stdin.close()
    return stdout


def remote_ls(remote_dirpath: str | None = None) -> list[str]:
    if remote_dirpath is None:
        local_dirpath = os.getcwd()
        remote_dirpath = get_remote_filepath(local_dirpath) + "/"

    stdout = execute_command(f"ls {remote_dirpath}", verbose=False)
    filepath_list = stdout.split("\n")
    filepath_list = [remote_dirpath + i for i in filepath_list]
    return filepath_list


def execute_local_script_on_remote(script_dict: dict[str, str], remote_dirpath: str | None = None):
    local_filepath_list = list(script_dict.keys())
    client = SSHClient(
        local_filepath_list=local_filepath_list,
    )
    client.put()
    remote_filepath_list = client.remote_filepath_list

    for remote_filepath_i, command_i in zip(remote_filepath_list, script_dict.values(), strict=False):
        execute_command(
            f"chmod +x {remote_filepath_i} && {command_i} && rm {remote_filepath_i}",
            remote_dirpath=remote_dirpath,
            cd=True,
        )


def put_file(local_filepath: str, setting: SSH_SETTING = SSH_SETTING()):
    client = SSHClient([local_filepath], setting=setting)
    client.put()


class Target:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def load(self):
        with self.open(mode="r") as f:
            data = json.load(f)
        return data

    def dump(self, data: Any):
        data = json.dumps(data)
        with self.open(mode="w") as f:
            f.write(data)

    def exists(self) -> bool:
        return os.path.exists(self.filepath)

    def open(self, mode: str = "r") -> IO[str] | IO[bytes]:
        with open(self.filepath, mode) as f:
            return f


class SSHTarget(Target):
    """
    Target for checking the existence of a file on a remote server via SSH.
    """

    def exists(self) -> bool:
        """
        Check if the target file exists on the remote server.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        with get_sftp_connection() as sftp:
            try:
                sftp.stat(self.filepath)
                return True
            except FileNotFoundError:
                return False

    @contextmanager
    def open(self, mode: str = "r") -> Iterator[IO[str]]:
        """
        Open the target file on the remote server.

        Args:
            mode (str): The mode in which the file is opened.
                        'r' for reading, 'w' for writing.

        Returns:
            io.StringIO or io.BytesIO: A file-like object.
        """
        with get_sftp_connection() as sftp:
            if mode == "r":
                try:
                    with sftp.open(self.filepath, "r") as remote_file:
                        content = remote_file.read()
                        if isinstance(content, bytes):
                            content = content.decode("utf-8")
                        yield to_stringio(content)
                except Exception as err:
                    raise FileNotFoundError(self.filepath) from err


def to_stringio(initial: str | bytearray | memoryview) -> io.StringIO:
    if isinstance(initial, str):
        return io.StringIO(initial)

    b = bytes(initial)  # bytearray / memoryview -> bytes
    return io.StringIO(b.decode("utf-8"))  # 必要なら encoding を変える

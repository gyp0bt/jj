import glob
import os
from pathlib import Path
from typing import Optional

from .ssh import SSH_SETTING, SSHClient

TOOL_DIRPATH = Path(__file__).parents[3] / "tools"
NORMALIZE_FILE_PY = TOOL_DIRPATH / "normalize_file.py"


def sget_single(
    basename: str, hostname: Optional[str] = None, version: Optional[str] = None
):
    target_ext_list = [
        ".png",
        ".cas.h5",
        ".dat.h5",
        ".xy",
        ".out",
        ".inp",
        ".dat",
        ".sta",
        ".par",
        ".msg",
        ".pes",
        ".odb",
        ".csv",
        ".aedt",
        ".json",
    ]

    client = SSHClient([], setting=SSH_SETTING(_hostname=hostname))
    remote_filepath_list = client.remote_ls()
    remote_filepath_list = [
        i for i in remote_filepath_list if any([i.endswith(j) for j in target_ext_list])
    ]

    # print(remote_filepath_list)
    remote_filepath_list = [i for i in remote_filepath_list if basename in i]
    if version:
        remote_filepath_list = [i for i in remote_filepath_list if version in i]
    # print(remote_filepath_list)

    local_dirpath = os.getcwd()
    local_filepath_list = [
        local_dirpath + "\\" + os.path.basename(i) for i in remote_filepath_list
    ]

    # print(remote_filepath_list)

    client = SSHClient(local_filepath_list, setting=SSH_SETTING(_hostname=hostname))
    client.get()


def sput(hostname: Optional[str] = None):
    setting = SSH_SETTING(_hostname=hostname)

    target_ext_list = ["*.inp", "*.msh", "*.json", "*.jcf", "*.k", "*.key", "*.cas.h5", "*.jou"]
    except_ext_list = [".odb.json"]
    local_filepath_list = []

    for i in target_ext_list:
        local_filepath_list += list(glob.glob(i))

    local_filepath_list = [
        i for i in local_filepath_list if all([j not in i for j in except_ext_list])
    ]

    # print(local_filepath_list)
    os.system(f"cp {NORMALIZE_FILE_PY} ./")
    local_filepath_list += ["normalize_file.py"]

    client = SSHClient(local_filepath_list, setting=setting)
    client.put()

    for i in target_ext_list:
        if i in ["*.msh"]:
            continue
        if not any([j.startswith(i) for j in local_filepath_list]):
            continue
        client.execute_command(f"ls {i} " + "|xin python normalize_file.py {}", cd=True)

    client.execute_command("rm normalize_file.py", cd=True)
    os.system("rm normalize_file.py")

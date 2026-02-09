from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import requests


class MatDbApiError(RuntimeError):
    """mat-db API 呼び出し失敗."""


def default_user_props() -> dict[str, Any]:
    # default_factory は「引数なし関数」
    return {
        "製品": "製品A",
        "事業部": "事業部A",
        "案件": "案件A",
        "依頼番号": "abc",
    }


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class CreateEntityRequest:
    # ---- API が要求するキー名に合わせる ----
    id: str
    name: str
    body: str

    # ---- 以下はデフォルト埋めで undefined を根絶 ----
    entityType: str = "Material"

    sysTags: list[str] = field(default_factory=list)
    userTags: list[str] = field(default_factory=list)

    sysProps: dict[str, Any] = field(default_factory=dict)
    userProps: dict[str, Any] = field(default_factory=default_user_props)

    remark: str = "POST-APIテスト"

    domain: str = "abaqus_inp"
    domainSource: str = "curation"
    domainConfidence: float = 1.0

    createdAt: str = field(default_factory=utc_now_iso)
    updatedAt: str = field(default_factory=utc_now_iso)

    # ---- requests に投げる用 ----
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "body": self.body,
            "entityType": self.entityType,
            "sysTags": self.sysTags,
            "userTags": self.userTags,
            "sysProps": self.sysProps,
            "userProps": self.userProps,
            "remark": self.remark,
            "domain": self.domain,
            "domainSource": self.domainSource,
            "domainConfidence": self.domainConfidence,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }


def login(*, base_url: str, username: str, password: str) -> str:
    r = requests.post(
        base_url.rstrip("/") + "/api/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    data = r.json()
    if r.status_code != 200:
        raise MatDbApiError(data.get("error", f"HTTP {r.status_code}"))
    return data["token"]


def create_entity(
    *,
    base_url: str,
    token: str,
    entity: dict[str, Any],
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    if not entity.get("id") or not entity.get("name"):
        raise ValueError("entity には 'id' と 'name' が必須です")

    url = base_url.rstrip("/") + "/api/entities"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    resp = requests.post(
        url,
        headers=headers,
        data=json.dumps(entity, ensure_ascii=False),
        timeout=timeout_s,
    )

    payload = resp.json()
    if resp.status_code == 201:
        return payload["entity"]

    raise MatDbApiError(payload.get("error", f"HTTP {resp.status_code}"))


def read_args_from_csv(csv_path: str) -> list[CreateEntityRequest]:
    df = pd.read_csv(csv_path)
    request_list = []
    for i, (_, row) in enumerate(df.iterrows()):
        args = {
            k: row[k]
            for k in df.columns
            if k not in ["bodypath", "userTags"] and not k.startswith("userProps")
        }
        user_props = {
            k.replace("userProps", ""): row[k]
            for k in df.columns
            if k.startswith("userProps")
        }
        user_tags = row["userTags"].replace(" ", "").split(",")
        with open(row["bodypath"]) as f:
            body = f.read()
        req = CreateEntityRequest(
            body=body, userTags=user_tags, userProps=user_props, **args
        )
        request_list.append(req)

    return request_list


if __name__ == "__main__":
    base_url = "http://localhost:3000"
    token = login(base_url=base_url, username="admin", password="admin123")

    for req in read_args_from_csv("assets/post_entity_args_template.csv"):
        created = create_entity(base_url=base_url, token=token, entity=req.to_dict())
        print(created["id"], created["name"])

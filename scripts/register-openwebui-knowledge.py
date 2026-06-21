import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import jwt
import requests


WEBUI_URL = "http://127.0.0.1:38127"
USER_ID = "c1694a29-3304-4a08-892a-1960cf933a5b"
SECRET_PATH = Path("/app/backend/.webui_secret_key")
DOC_PATH = Path("/host/projects/personal/ai-local/knowledge/api-e-alece-padroes-projetos-futuros.md")
KNOWLEDGE_NAME = "Padroes Laravel API - api-e-alece"
KNOWLEDGE_DESCRIPTION = (
    "Arquitetura, documentacao, testes e workflow para projetos Laravel API futuros, "
    "baseados no projeto api-e-alece."
)


def token() -> str:
    secret = SECRET_PATH.read_text(encoding="utf-8").strip()
    payload = {
        "id": USER_ID,
        "iat": datetime.now(timezone.utc),
        "jti": "local-knowledge-seed",
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def request(method: str, path: str, auth_token: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {auth_token}"
    response = requests.request(
        method,
        f"{WEBUI_URL}{path}",
        headers=headers,
        timeout=120,
        **kwargs,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text[:1000]}")
    return response.json()


def find_knowledge(auth_token: str):
    result = request(
        "GET",
        "/api/v1/knowledge/search",
        auth_token,
        params={"query": KNOWLEDGE_NAME, "page": 1},
    )
    for item in result.get("items", []):
        if item.get("name") == KNOWLEDGE_NAME:
            return item
    return None


def create_or_get_knowledge(auth_token: str):
    knowledge = find_knowledge(auth_token)
    if knowledge:
        return knowledge

    return request(
        "POST",
        "/api/v1/knowledge/create",
        auth_token,
        json={
            "name": KNOWLEDGE_NAME,
            "description": KNOWLEDGE_DESCRIPTION,
            "access_grants": [],
        },
    )


def doc_hash() -> str:
    return hashlib.sha256(DOC_PATH.read_bytes()).hexdigest()


def find_uploaded_file(auth_token: str, expected_hash: str):
    try:
        files = request(
            "GET",
            "/api/v1/files/search",
            auth_token,
            params={
                "filename": DOC_PATH.name,
                "content": "false",
                "skip": 0,
                "limit": 50,
            },
        )
    except RuntimeError as exc:
        if "404" in str(exc):
            return None
        raise

    for item in files:
        if item.get("filename") == DOC_PATH.name and item.get("hash") == expected_hash:
            return item
    return None


def upload_file(auth_token: str, expected_hash: str):
    existing = find_uploaded_file(auth_token, expected_hash)
    if existing:
        return existing

    metadata = {
        "source": "api-e-alece",
        "kind": "project-standards",
        "path": str(DOC_PATH),
        "updated_by": "register-openwebui-knowledge.py",
    }
    with DOC_PATH.open("rb") as file_handle:
        return request(
            "POST",
            "/api/v1/files/",
            auth_token,
            params={"process": "true", "process_in_background": "false"},
            data={"metadata": json.dumps(metadata)},
            files={"file": (DOC_PATH.name, file_handle, "text/markdown")},
        )


def knowledge_file_ids(knowledge: dict) -> set[str]:
    return {
        item.get("id")
        for item in knowledge.get("files") or []
        if item.get("id")
    }


def add_file_to_knowledge(auth_token: str, knowledge_id: str, file_id: str):
    knowledge = request("GET", f"/api/v1/knowledge/{knowledge_id}", auth_token)
    if file_id in knowledge_file_ids(knowledge):
        return knowledge

    return request(
        "POST",
        f"/api/v1/knowledge/{knowledge_id}/file/add",
        auth_token,
        json={"file_id": file_id},
    )


def main():
    if not DOC_PATH.exists():
        raise FileNotFoundError(DOC_PATH)

    auth_token = token()
    expected_hash = doc_hash()
    knowledge = create_or_get_knowledge(auth_token)
    file_item = upload_file(auth_token, expected_hash)
    result = add_file_to_knowledge(auth_token, knowledge["id"], file_item["id"])

    print(json.dumps({
        "knowledge_id": result["id"],
        "knowledge_name": result["name"],
        "file_id": file_item["id"],
        "file_name": file_item["filename"],
        "file_hash": expected_hash,
        "registered_at": int(time.time()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

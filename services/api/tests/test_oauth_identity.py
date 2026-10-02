from types import SimpleNamespace

from fastapi import HTTPException

import auth
from database import users_table


def test_external_oauth_identity_is_used_after_local_jwt_rejection(monkeypatch, existing_user):
    user = users_table.get(doc_id=existing_user["id"])
    monkeypatch.setattr(auth, "decode_access_token", lambda token: (_ for _ in ()).throw(HTTPException(401)))
    monkeypatch.setattr(auth, "_external_identity", lambda token: user if token == "oauth-token" else None)
    result = auth.get_current_user("Bearer oauth-token")
    assert result.doc_id == existing_user["id"]

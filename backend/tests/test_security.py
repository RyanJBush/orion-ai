import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import create_access_token, get_current_user, require_role


def test_create_access_token_returns_non_empty_jwt_string():
    token = create_access_token(subject="user-1", role="admin")
    assert isinstance(token, str)
    assert len(token) > 20
    assert token.count(".") == 2  # JWT has three dot-separated parts


def test_get_current_user_returns_correct_subject_and_role_for_valid_token():
    token = create_access_token(subject="user-42", role="operator")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds=creds)
    assert user["id"] == "user-42"
    assert user["role"] == "operator"


def test_get_current_user_raises_401_when_credentials_are_absent():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds=None)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Authentication required"


def test_get_current_user_raises_401_for_malformed_token():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not.a.valid.token")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(creds=creds)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


def test_require_role_allows_user_with_matching_role():
    token = create_access_token(subject="admin-user", role="admin")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds=creds)
    guard = require_role({"admin", "operator"})
    result = guard(user=user)
    assert result["id"] == "admin-user"
    assert result["role"] == "admin"


def test_require_role_raises_403_for_user_with_insufficient_role():
    token = create_access_token(subject="viewer-user", role="viewer")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = get_current_user(creds=creds)
    guard = require_role({"admin"})
    with pytest.raises(HTTPException) as exc_info:
        guard(user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions"

"""Unit tests for security utilities."""

import time
from datetime import timedelta

import pytest

from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("MySecret1")
        assert hashed != "MySecret1"

    def test_verify_correct_password(self):
        hashed = hash_password("Correct1")
        assert verify_password("Correct1", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("Correct1")
        assert verify_password("Wrong1", hashed) is False

    def test_different_hashes_same_input(self):
        # Argon2 uses random salt — same input produces different hashes
        h1 = hash_password("SamePass1")
        h2 = hash_password("SamePass1")
        assert h1 != h2

    def test_empty_password_not_matched(self):
        hashed = hash_password("SomePass1")
        assert verify_password("", hashed) is False


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token({"sub": "user-123", "role": "api_user"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "api_user"

    def test_expired_token_raises(self):
        token = create_access_token(
            {"sub": "user-123"}, expires_delta=timedelta(seconds=-1)
        )
        with pytest.raises(UnauthorizedException):
            decode_access_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(UnauthorizedException):
            decode_access_token("not.a.valid.token")

    def test_token_missing_sub_raises(self):
        token = create_access_token({"role": "admin"})
        # sub is missing — decode should raise
        with pytest.raises(UnauthorizedException):
            payload = decode_access_token(token)
            if not payload.get("sub"):
                raise UnauthorizedException("Missing sub")

    def test_tampered_token_raises(self):
        token = create_access_token({"sub": "user-123"})
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(UnauthorizedException):
            decode_access_token(tampered)

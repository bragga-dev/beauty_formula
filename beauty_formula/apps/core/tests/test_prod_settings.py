"""Garante que prod.py não perde a configuração de JWT definida em base.py."""
import importlib

import pytest


def test_prod_keeps_refresh_rotation_and_blacklist(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@localhost:5432/db")
    monkeypatch.setenv("CSRF_TRUSTED_ORIGINS", "https://example.com")
    prod = importlib.import_module("beauty_formula.config.settings.prod")
    prod = importlib.reload(prod)
    jwt = prod.NINJA_JWT
    assert jwt["ROTATE_REFRESH_TOKENS"] is True
    assert jwt["BLACKLIST_AFTER_ROTATION"] is True
    assert jwt["SIGNING_KEY"]
    assert jwt["USER_ID_FIELD"] == "id"
    assert prod.DEBUG is False and prod.SECURE_SSL_REDIRECT is True
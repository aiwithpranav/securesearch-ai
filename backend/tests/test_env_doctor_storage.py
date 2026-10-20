"""The env doctor also checks the Phase 3 storage settings."""
import pytest

from app.core.config import settings
from app.core.env_doctor import check_env


def test_env_doctor_reports_missing_storage_settings(capsys, monkeypatch):
    monkeypatch.setattr(settings, "s3_bucket", "CHANGE_ME")
    monkeypatch.setattr(settings, "s3_secret_key", "CHANGE_ME")
    with pytest.raises(SystemExit) as excinfo:
        check_env()
    assert excinfo.value.code == 1
    out = capsys.readouterr().out
    assert "S3_BUCKET is missing or still set to CHANGE_ME" in out
    assert "S3_SECRET_KEY is missing or still set to CHANGE_ME" in out
    assert settings.s3_access_key not in out  # secrets are never printed


def test_env_doctor_reports_unreachable_storage(capsys, monkeypatch):
    monkeypatch.setattr(settings, "s3_endpoint_url", "http://127.0.0.1:1")
    with pytest.raises(SystemExit):
        check_env()
    assert "Object storage is unreachable" in capsys.readouterr().out

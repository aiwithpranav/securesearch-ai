import pytest
from app.core.env_doctor import check_env
from app.core.config import settings

def test_env_doctor_fails_on_missing_or_short_keys(capsys, monkeypatch):
    monkeypatch.setattr(settings, "app_secret_key", "short")
    monkeypatch.setattr(settings, "jwt_secret_key", "CHANGE_ME")
    monkeypatch.setattr(settings, "postgres_user", "CHANGE_ME")
    
    with pytest.raises(SystemExit) as excinfo:
        check_env()
    
    assert excinfo.value.code == 1
    
    captured = capsys.readouterr()
    output = captured.out
    
    assert "APP_SECRET_KEY is too short" in output
    assert "JWT_SECRET_KEY is missing or still set to CHANGE_ME" in output
    assert "POSTGRES_USER is missing or still set to CHANGE_ME" in output

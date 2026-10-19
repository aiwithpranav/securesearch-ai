from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Required in .env (the env doctor checks these) ---
    app_env: str = "CHANGE_ME"
    app_secret_key: str = "CHANGE_ME"
    jwt_secret_key: str = "CHANGE_ME"
    postgres_user: str = "CHANGE_ME"
    postgres_password: str = "CHANGE_ME"
    postgres_db: str = "CHANGE_ME"
    database_url: str = "CHANGE_ME"
    redis_url: str = "CHANGE_ME"
    smtp_host: str = "CHANGE_ME"
    smtp_port: str = "CHANGE_ME"
    frontend_origin: str = "http://localhost:3000"

    # --- Only needed by the demo-user seed script (Phase 2B) ---
    seed_user_password: str = ""

    # --- Auth tuning knobs. Safe defaults; override in .env only if needed. ---
    access_token_minutes: int = 15  # short-lived access token
    refresh_session_hours: int = 24  # "Remember me" unchecked: server-side cap
    refresh_remember_days: int = 7  # "Remember me" checked (blueprint: default 7, max 30)
    reset_token_minutes: int = 30  # password reset link lifetime
    invite_token_hours: int = 72  # invite link lifetime
    login_max_failures: int = 5  # wrong passwords before temporary lockout
    login_lockout_minutes: int = 15
    login_ip_limit_per_minute: int = 30
    forgot_ip_limit_per_15min: int = 5
    min_password_length: int = 12
    mail_from: str = "SecureSearch AI <noreply@securesearch.local>"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

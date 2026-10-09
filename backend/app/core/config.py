from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

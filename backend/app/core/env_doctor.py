import sys
import socket
from .config import settings

def check_env():
    errors = []
    
    # Check for placeholders
    variables_to_check = [
        "APP_ENV", "APP_SECRET_KEY", "JWT_SECRET_KEY",
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
        "DATABASE_URL", "REDIS_URL", "SMTP_HOST", "SMTP_PORT",
        "FRONTEND_ORIGIN"
    ]
    for var in variables_to_check:
        val = getattr(settings, var.lower(), "CHANGE_ME")
        if val == "CHANGE_ME":
            errors.append(f"{var} is missing or still set to CHANGE_ME. Add it to .env, then restart.")
    
    # Check secret keys
    app_key = settings.app_secret_key
    jwt_key = settings.jwt_secret_key
    if app_key != "CHANGE_ME" and len(app_key) < 32:
        errors.append("APP_SECRET_KEY is too short. It must be at least 32 characters long.")
    if jwt_key != "CHANGE_ME" and len(jwt_key) < 32:
        errors.append("JWT_SECRET_KEY is too short. It must be at least 32 characters long.")
    if app_key != "CHANGE_ME" and jwt_key != "CHANGE_ME" and app_key == jwt_key:
        errors.append("APP_SECRET_KEY and JWT_SECRET_KEY must be different.")
    
    # Check redis connection via simple socket test (since we don't want to rely on redis library being initialized)
    if settings.redis_url != "CHANGE_ME":
        try:
            url = settings.redis_url.split("://")[1].split("/")[0]
            host, port = url.split(":") if ":" in url else (url, 6379)
            with socket.create_connection((host, int(port)), timeout=3):
                pass
        except Exception:
            errors.append("Redis is unreachable. Ensure the service is running and REDIS_URL is correct.")

    # Check postgres connection
    if settings.database_url != "CHANGE_ME":
        try:
            url_part = settings.database_url.split("@")[1].split("/")[0]
            host, port = url_part.split(":") if ":" in url_part else (url_part, 5432)
            with socket.create_connection((host, int(port)), timeout=3):
                pass
        except Exception:
            errors.append("Postgres is unreachable. Ensure the service is running and DATABASE_URL is correct.")

    if errors:
        for error in errors:
            print(error)
        sys.exit(1)

if __name__ == "__main__":
    check_env()

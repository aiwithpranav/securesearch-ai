# SecureSearch AI

## Quick start (backend)
1. Copy `.env.example` to `.env`
2. Generate two secrets with `node -e "console.log(require('crypto').randomBytes(48).toString('base64url'))"` and place them in `.env` for `APP_SECRET_KEY` and `JWT_SECRET_KEY`.
3. Run `docker compose up --build`

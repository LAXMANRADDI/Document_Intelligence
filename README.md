# Auth Service (FastAPI + JWT)

A self-contained authentication API: signup, login, access/refresh tokens, logout,
and a protected `/auth/me` endpoint. Uses SQLAlchemy + SQLite by default (swap in
Postgres by changing one env var), bcrypt password hashing, and JWTs signed with HS256.

## Project structure

```
fastapi-auth-service/
├── app/
│   ├── main.py        # FastAPI app + routes
│   ├── config.py       # Settings (env vars)
│   ├── database.py     # SQLAlchemy engine/session
│   ├── models.py       # User, RefreshToken tables
│   ├── schemas.py       # Pydantic request/response models
│   ├── security.py     # Password hashing + JWT create/decode
│   ├── crud.py           # DB access functions
│   └── deps.py            # get_db / get_current_user dependencies
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## 1. Run locally (no Docker)

Requires Python 3.11+.

```bash
cd fastapi-auth-service
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# generate a real secret and put it in .env:
python3 -c "import secrets; print(secrets.token_hex(32))"

mkdir -p data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for interactive Swagger UI.

## 2. Run with Docker

```bash
cd fastapi-auth-service
cp .env.example .env
# edit .env and set a real SECRET_KEY (see command above)

docker compose up --build
```

The API is now at `http://localhost:8000`. The SQLite file persists in the
`db_data` Docker volume across restarts.

To stop: `docker compose down` (add `-v` to also wipe the database volume).

## 3. API reference

| Method | Path            | Auth required | Description                          |
|--------|-----------------|----------------|--------------------------------------|
| POST   | `/auth/signup`  | No             | Create a new user                    |
| POST   | `/auth/login`   | No             | Get access + refresh tokens          |
| POST   | `/auth/refresh` | No (needs refresh token) | Exchange refresh token for new access token |
| POST   | `/auth/logout`  | No (needs refresh token) | Revoke a refresh token               |
| GET    | `/auth/me`      | Yes (Bearer)   | Get the current user's profile       |
| GET    | `/health`       | No             | Liveness check                       |

### Signup

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "supersecret123"}'
```

### Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "supersecret123"}'
```

Returns:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Access a protected route

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Refresh an expired access token

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

### Logout (revoke refresh token)

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}'
```

Note: in Swagger UI (`/docs`), use the "Authorize" button and paste the raw
access token — the login endpoint takes JSON, not a form, so Swagger's
automatic password-flow login won't work, but manually pasting the token does.

## 4. Configuration (`.env`)

| Variable                      | Default                        | Notes                                    |
|--------------------------------|---------------------------------|-------------------------------------------|
| `SECRET_KEY`                   | placeholder                     | **Must** be a long random value in prod  |
| `ALGORITHM`                    | `HS256`                          |                                            |
| `ACCESS_TOKEN_EXPIRE_MINUTES`  | `30`                             | Short-lived, sent on every request         |
| `REFRESH_TOKEN_EXPIRE_DAYS`    | `7`                              | Long-lived, used only to mint new access tokens |
| `DATABASE_URL`                 | `sqlite:///./data/app.db`       | Point to Postgres for production, e.g. `postgresql://user:pass@host:5432/dbname` |

## 5. Moving this to production (things you'll want to do yourself)

- **Database**: swap SQLite for managed Postgres (RDS, Cloud SQL, etc.). Set
  `DATABASE_URL` accordingly and add `psycopg2-binary` to `requirements.txt`.
- **Migrations**: introduce Alembic once the schema needs to evolve — right
  now tables are created via `Base.metadata.create_all()` at startup, which
  is fine for a fresh dev/staging DB but not for versioned schema changes.
- **Secrets**: never commit `.env`; inject `SECRET_KEY` and `DATABASE_URL`
  via your platform's secret manager (AWS Secrets Manager, Doppler, etc.).
- **TLS**: put this behind a reverse proxy (Nginx, Caddy, or your cloud
  load balancer) that terminates HTTPS — the app itself serves plain HTTP.
- **Process manager**: run with multiple workers in production, e.g.
  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4`, or use
  Gunicorn with the Uvicorn worker class.
- **Rate limiting**: add a reverse-proxy or middleware rate limit on
  `/auth/login` and `/auth/signup` to blunt brute-force/credential-stuffing attempts.
- **Refresh token rotation**: current implementation reuses the same refresh
  token until it expires or is revoked; for tighter security, issue a new
  refresh token on every `/auth/refresh` call and revoke the old one.
- **Password reset / email verification**: not included — add endpoints plus
  an email-sending provider (SES, Postmark, etc.) if needed.

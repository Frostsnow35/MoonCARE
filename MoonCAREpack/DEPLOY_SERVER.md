# MoonCARE Server Deployment

> Change date: 2026-05-21  
> Target path: `/www/wwwroot/MoonCARE`  
> Package source: upload `MoonCAREpack`, then rename it to `MoonCARE` on the server  
> Status: ready for Docker Compose deployment; secrets must be filled on the server

## 1. Place The Package

After uploading the whole `MoonCAREpack` folder to the server, rename it:

```bash
mkdir -p /www/wwwroot
mv /www/wwwroot/MoonCAREpack /www/wwwroot/MoonCARE
cd /www/wwwroot/MoonCARE
```

If your upload tool places it elsewhere, move the entire folder to `/www/wwwroot/MoonCARE` before running the commands below.

## 2. Create Server Environment

```bash
cd /www/wwwroot/MoonCARE
cp .env.example .env
chmod 600 .env
```

Edit `.env` on the server and replace every placeholder. Required production values include:

| Variable | Required | Notes |
| --- | --- | --- |
| `DB_PASSWORD` | yes | Strong PostgreSQL password. |
| `SECRET_KEY` | yes | Long random JWT and email-code hash secret. |
| `AUTH_EMAIL_DELIVERY_MODE` | yes | Keep `smtp` for real email verification. |
| `SMTP_USERNAME` | yes | For 163 Mail, use the sender account. |
| `SMTP_PASSWORD` | yes | 163 SMTP authorization code. Do not commit this value. |
| `SMTP_FROM_EMAIL` | yes | Must equal `SMTP_USERNAME` for 163 Mail. |

For the verified 163 Mail setup:

```env
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USE_TLS=false
SMTP_USE_SSL=true
SMTP_USERNAME=your_sender@163.com
SMTP_PASSWORD=your_163_authorization_code
SMTP_FROM_EMAIL=your_sender@163.com
```

## 3. Start The Service

```bash
cd /www/wwwroot/MoonCARE
docker compose config
docker compose build
docker compose up -d
docker compose logs -f app
```

The packaged `Dockerfile` uses the existing `frontend/dist` build. It does not require frontend source files or `npm install` on the server.

## 4. Verify Health And Email Code

Local container health:

```bash
curl -fsS http://127.0.0.1:8000/health
```

Email verification endpoint:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/email-code/send" \
  -H "Content-Type: application/json" \
  -d '{"email":"recipient@example.com","purpose":"register"}'
```

Expected response:

```json
{"code":200,"data":{"expires_in_seconds":600,"cooldown_seconds":60},"message":"验证码已发送，请查收邮箱"}
```

## 5. Reverse Proxy Notes

Point your reverse proxy to `127.0.0.1:8000`.

Required behavior:

| Route | Proxy target | Notes |
| --- | --- | --- |
| `/` | `http://127.0.0.1:8000` | FastAPI serves packaged frontend files. |
| `/api/v1/*` | `http://127.0.0.1:8000` | REST APIs. |
| `/api/v1/chat/ws/*` | `ws://127.0.0.1:8000` | Must enable WebSocket upgrade. |
| `/healthz` | `http://127.0.0.1:8000` | Health check. |

## 6. Security Notes

| Risk | Required action |
| --- | --- |
| SMTP authorization code leak | Keep it only in `/www/wwwroot/MoonCARE/.env` or server secret manager. |
| Weak JWT secret | Replace `SECRET_KEY` with a long random value before first production start. |
| Public database port | Keep `POSTGRES_BIND_ADDR=127.0.0.1` unless there is a strong reason to expose it. |
| Verification abuse | Keep resend cooldown and max attempts enabled; add reverse-proxy rate limiting before public launch. |
| Logs | Do not print full email codes, tokens, chat content, or health privacy data in production logs. |

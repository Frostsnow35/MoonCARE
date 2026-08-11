# MoonCARE Email Verification Deployment

> Change date: 2026-05-21  
> Scope: registration email code and password reset email code in packaged server deployment  
> Status: ready for deployment; requires server environment variables

## Why

MoonCARE registration and password reset use email verification codes. The package must include the configuration contract, but must not include real SMTP authorization codes.

## Required Variables

Copy `.env.example` to `.env` on the server and replace these values:

| Variable | Type | Required | Default / Example | Description |
| --- | --- | --- | --- | --- |
| `AUTH_EMAIL_DELIVERY_MODE` | string | yes | `smtp` | Use `smtp` for real email delivery. `log` is only for local `DEBUG=true` development. |
| `SMTP_HOST` | string | yes | `smtp.163.com` | SMTP server host. |
| `SMTP_PORT` | int | yes | `465` | 163 Mail works with SSL on port 465 in the verified local setup. |
| `SMTP_USERNAME` | string | yes | `replace_with_sender_163_email` | SMTP login account. |
| `SMTP_PASSWORD` | string | yes | `replace_with_163_smtp_authorization_code` | SMTP authorization code. Do not commit this value. |
| `SMTP_FROM_EMAIL` | string | yes | `replace_with_sender_163_email` | Sender address. For 163 Mail, it must equal `SMTP_USERNAME`. |
| `SMTP_USE_TLS` | bool | yes | `false` | STARTTLS switch. Keep false when using 465 SSL. |
| `SMTP_USE_SSL` | bool | yes | `true` | SSL switch for port 465. |
| `SECRET_KEY` | string | yes | `replace_with_long_random_secret_key` | Also protects email-code hashes and JWT signatures. Use a strong server-only secret. |

## Verified 163 Mail Settings

```env
AUTH_EMAIL_DELIVERY_MODE=smtp
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USERNAME=your_sender@163.com
SMTP_PASSWORD=your_163_authorization_code
SMTP_FROM_EMAIL=your_sender@163.com
SMTP_USE_TLS=false
SMTP_USE_SSL=true
```

## Deployment Check

After starting the server, verify the endpoint with a real recipient:

```bash
curl -X POST "https://your-domain.example/api/v1/auth/email-code/send" \
  -H "Content-Type: application/json" \
  -d '{"email":"recipient@example.com","purpose":"register"}'
```

Expected response:

```json
{"code":200,"data":{"expires_in_seconds":600,"cooldown_seconds":60},"message":"验证码已发送，请查收邮箱"}
```

## Risks

| Risk | Mitigation |
| --- | --- |
| SMTP authorization code leaked | Keep it only in server `.env` or platform secrets; never commit it. |
| 163 sender mismatch | Keep `SMTP_FROM_EMAIL` equal to `SMTP_USERNAME`. |
| Port 587 timeout | Use 465 SSL for 163 Mail unless the server network confirms STARTTLS works. |
| Mail abuse / spam | Keep resend cooldown and max attempts enabled; consider adding IP rate limits before public launch. |
| User enumeration | Password reset endpoint returns the same success message for missing accounts. |

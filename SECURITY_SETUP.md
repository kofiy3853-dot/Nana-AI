# Security Setup Guide

## Step 1: Generate Password Hash

Run the password generator:
```bash
cd backend
.venv\Scripts\python generate_password.py
```

## Step 2: Update .env File

Copy `.env.example` to `.env` and update:
```bash
JWT_SECRET_KEY=<generate a random 32+ character string>
NANA_PASSWORD_HASH=<output from generate_password.py>
ALLOWED_ORIGINS=http://localhost:5173,https://your-app.vercel.app
```

## Step 3: Test Authentication

Test login endpoint:
```bash
curl -X POST http://localhost:3001/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

## Step 4: Use Token

Copy the `access_token` from the response and use it:
```bash
curl -X POST http://localhost:3001/api/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"command":"test","intent":"unknown"}'
```

## Security Notes

- **Change default password immediately**
- **Use strong JWT secret (32+ characters)**
- **Never commit .env file to git**
- **Update ALLOWED_ORIGINS for production**
- **Tokens expire after 24 hours**

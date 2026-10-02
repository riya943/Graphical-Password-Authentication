# Graphical Password Authentication

Flask + SQLite project with two-factor authentication: a normal password and an ordered graphical password sequence.

## Added in this version
- Email collected during registration.
- 4x4 graphical password grid with 16 local visual pattern tiles (no emojis and no external image dependency).
- Clicking a selected tile again removes it from the sequence and renumbers the remaining selections.
- Password reset from the login page.
- Reset email contains a one-time link that expires after 30 minutes.
- Reset page changes both the normal password and graphical password.
- Existing `database.db` files are upgraded automatically with the new email/reset-token tables.
- Passwords and graphical sequences remain hashed.

## Windows setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Email setup for password reset

The reset feature sends email through SMTP. For Gmail, use a Google **App Password**, not your normal Gmail password.

PowerShell example:

```powershell
$env:SECRET_KEY="replace-with-a-long-random-secret"
$env:MAIL_SERVER="smtp.gmail.com"
$env:MAIL_PORT="587"
$env:MAIL_USERNAME="your-email@gmail.com"
$env:MAIL_PASSWORD="your-16-character-app-password"
python app.py
```

Keep these values private. Do not commit them to GitHub.

If email is not configured, the rest of the project still runs, but the reset email cannot be sent.

## Graphical password

The 4x4 grid contains 16 local SVG patterns. The user selects at least 3 in a specific order. The exact sequence is hashed in the database and must be reproduced during login.

## Important

This is an educational/local project. For production, add CSRF protection, rate limiting, HTTPS, secure session cookies, stronger email verification, account lockout/monitoring, and proper secret management.

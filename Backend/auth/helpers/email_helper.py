import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from auth.config import get_config

logger = logging.getLogger(__name__)
config = get_config()

from auth.constants.roles import STAKEHOLDER_ROLES

# Common client-side labels / typos → canonical DB role names.
# Keep this conservative: only map known equivalents.
ROLE_ALIASES = {
    "Principle": "Principal",
    "Counsellor": "Psychologist",
    "Counselor": "Psychologist",
    "Teacher": "Class Teacher",
    "Behaviour Analyst": "Behaviour Scientist",
}


def normalize_role_name(role_name: str | None) -> str | None:
    if not role_name:
        return role_name
    role_name = role_name.strip()
    return ROLE_ALIASES.get(role_name, role_name)


def send_credentials_email(to_email: str, full_name: str, role_name: str, password: str) -> bool:
    """Send login credentials after admin approval. Returns True if sent (or skipped in dev)."""
    if not config.SMTP_HOST or not config.SMTP_FROM:
        logger.warning(
            "[SECURITY] SMTP not configured — temp password NOT logged. Use secure out-of-band delivery."
        )
        return False

    login_url = f"{config.FRONTEND_URL.rstrip('/')}/"
    subject = "Your Sentio Mind account is ready"
    body = f"""Hello {full_name},

Your Sentio Mind access has been approved as: {role_name}.

Sign in here: {login_url}

Email: {to_email}
Temporary password: {password}

Please change your password after your first login.

— Sentio Mind Team
"""

    msg = MIMEMultipart()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            if config.SMTP_USE_TLS:
                server.starttls()
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """Send password reset link. Token is only in the email body — never logged."""
    if not config.SMTP_HOST or not config.SMTP_FROM:
        logger.warning(
            "SMTP not configured — password reset for %s (link not sent)",
            to_email,
        )
        return False

    reset_url = (
        f"{config.FRONTEND_URL.rstrip('/')}/reset-password?token={reset_token}"
    )
    subject = "Reset your Sentio Mind password"
    body = f"""Hello,

We received a request to reset the password for your Sentio Mind account.

Reset your password here (link expires in 15 minutes):
{reset_url}

If you did not request this, you can safely ignore this email. Your password will not change.

— Sentio Mind Team
"""

    msg = MIMEMultipart()
    msg["From"] = config.SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            if config.SMTP_USE_TLS:
                server.starttls()
            if config.SMTP_USER and config.SMTP_PASSWORD:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_FROM, [to_email], msg.as_string())
        return True
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", to_email, e)
        return False

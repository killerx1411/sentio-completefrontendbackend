import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import get_config

logger = logging.getLogger(__name__)
config = get_config()

# Roles assignable during landing-page signup approval (educational + specialist)
# Canonical names must match `auth_enabler.roles.name` in the database.
STAKEHOLDER_ROLES = (
    "Principal",
    "Psychologist",
    "Class Teacher",
    "Behaviour Scientist",
)

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
            "SMTP not configured — credentials for %s (role=%s): password=%s",
            to_email,
            role_name,
            password,
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

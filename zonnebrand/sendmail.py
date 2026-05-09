import os
import resend
from typing import Optional
from dotenv import load_dotenv
import logging
logger = logging.getLogger(__name__)


# ── Configure the SDK once at import time ──────────────────────────────────────
# check_keys = load_dotenv("../.secrets/keys")
# if not check_keys:
#     load_dotenv(".secrets/keys")
# resend.api_key = os.getenv("RESEND_API_KEY")

# if not resend.api_key:
#     raise EnvironmentError(
#         "RESEND_API_KEY is not set. "
#         "Export it as an environment variable before running this module."
#     )

def send_email(
    to: str | list[str],
    subject: str,
    api_key: str = None,
    *,
    html: Optional[str] = None,
    text: Optional[str] = None,
    sender: str = "Zonnebrand <no-reply@skywalkflight.com>",
    cc: Optional[str | list[str]] = None,
    bcc: Optional[str | list[str]] = None,
    reply_to: Optional[str | list[str]] = None,
    attachments: Optional[list[dict]] = None,
    tags: Optional[list[dict]] = None,
) -> dict:
    """
    Send an email using the Resend API.

    Parameters
    ----------
    to         : Recipient address(es) — a string or list of strings.
    subject    : Email subject line.
    html       : HTML body of the email (use this or `text`, or both).
    text       : Plain-text body (fallback for clients that don't render HTML).
    sender     : "From" address. Must be from a verified Resend domain.
                 Format: "Name <email@yourdomain.com>"
    cc         : CC address(es).
    bcc        : BCC address(es).
    reply_to   : Reply-To address(es).
    attachments: List of attachment dicts, each with keys:
                     "filename" (str) and "content" (base64-encoded bytes or str).
    tags       : List of tag dicts: [{"name": "key", "value": "val"}, ...]

    Returns
    -------
    dict with the Resend response, including the email "id" on success.

    Raises
    ------
    ValueError  : If neither `html` nor `text` is provided.
    resend.exceptions.ResendError : On API-level errors.
    """
    logger.info('Sending status update mail.')
    if api_key is None:
        logger.error('RESEND_API_KEY is not set <return>')
        return
    if to is None:
        logger.error('To address is not set <return>')
        return

    if not html and not text:
        raise ValueError("Provide at least one of `html` or `text`.")

    # Normalise single strings to lists where the SDK expects lists
    def _listify(val):
        if val is None:
            return None
        return [val] if isinstance(val, str) else val

    # Set api key
    resend.api_key = api_key
    # Set other params
    params: resend.Emails.SendParams = {
        "from": sender,
        "to": _listify(to),
        "subject": subject,
    }

    if html:
        params["html"] = html
    if text:
        params["text"] = text
    if cc:
        params["cc"] = _listify(cc)
    if bcc:
        params["bcc"] = _listify(bcc)
    if reply_to:
        params["reply_to"] = _listify(reply_to)
    if attachments:
        params["attachments"] = attachments
    if tags:
        params["tags"] = tags

    response: resend.Emails.SendResponse = resend.Emails.send(params)
    return response


# ── Convenience wrappers ───────────────────────────────────────────────────────

def send_html_email(to: str | list[str], subject: str, html: str, api_key = None, **kwargs) -> dict:
    """Shortcut for sending an HTML-only email."""
    return send_email(to, subject, html=html, api_key=api_key, **kwargs)


def send_text_email(to: str | list[str], subject: str, text: str, api_key = None, **kwargs) -> dict:
    """Shortcut for sending a plain-text email."""
    return send_email(to, subject, text=text, api_key=api_key, **kwargs)


def send_email_with_attachment(
    to: str | list[str],
    subject: str,
    html: str,
    filepath: str,
    **kwargs,
) -> dict:
    """
    Send an email with a local file attached.

    Parameters
    ----------
    filepath : Absolute or relative path to the file to attach.
    """
    import base64
    from pathlib import Path

    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Attachment not found: {filepath}")

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    attachment = {"filename": path.name, "content": encoded}

    return send_email(to, subject, html=html, attachments=[attachment], **kwargs)



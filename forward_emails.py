import imaplib
import smtplib
import email
import os
import time
from email.message import EmailMessage
from email.header import decode_header, make_header
from datetime import datetime

# =============================
# CONFIG
# =============================
YAHOO_EMAIL = os.environ["YAHOO_EMAIL"]
YAHOO_APP_PASSWORD = os.environ["YAHOO_APP_PASSWORD"]

GMAIL_EMAIL = os.environ["GMAIL_EMAIL"]

IMAP_SERVER = "imap.mail.yahoo.com"
SMTP_SERVER = "smtp.mail.yahoo.com"
SMTP_PORT = 587

MAX_PER_RUN = 25  # keep safe to avoid limits
SLEEP_BETWEEN = 2  # seconds


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def decode_subject(raw_subject):
    if not raw_subject:
        return "(No Subject)"
    return str(make_header(decode_header(raw_subject)))


# =============================
# CONNECT IMAP
# =============================
log("=" * 60)
log("Starting Yahoo → Gmail forwarder")
log("=" * 60)

imap = imaplib.IMAP4_SSL(IMAP_SERVER)
imap.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
imap.select("INBOX")

status, messages = imap.search(None, "UNSEEN")
email_ids = messages[0].split()

log(f"Found {len(email_ids)} unread emails")

if not email_ids:
    log("No unread emails. Exiting.")
    imap.logout()
    exit()

email_ids = email_ids[:MAX_PER_RUN]
log(f"Processing {len(email_ids)} this run")

# =============================
# CONNECT SMTP
# =============================
def connect_smtp():
    smtp = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    smtp.starttls()
    smtp.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
    return smtp


smtp = connect_smtp()

# =============================
# PROCESS EMAILS
# =============================
for i, email_id in enumerate(email_ids, 1):
    try:
        status, msg_data = imap.fetch(email_id, "(RFC822)")
        raw_email = msg_data[0][1]
        original_msg = email.message_from_bytes(raw_email)

        subject = decode_subject(original_msg.get("Subject"))

        # Build clean forward message
        fwd = EmailMessage()
        fwd["From"] = YAHOO_EMAIL
        fwd["To"] = GMAIL_EMAIL
        fwd["Subject"] = f"FWD: {subject}"

        fwd.set_content(
            f"This email was automatically forwarded from Yahoo.\n\n"
            f"Original From: {original_msg.get('From')}\n"
            f"Original Subject: {subject}\n\n"
            f"The original message is attached."
        )

        # Attach original email intact
        fwd.add_attachment(
            raw_email,
            maintype="message",
            subtype="rfc822",
            filename="original_email.eml",
        )

        smtp.send_message(fwd)

        # Mark as seen ONLY after successful send
        imap.store(email_id, "+FLAGS", "\\Seen")

        log(f"[{i}/{len(email_ids)}] Forwarded: {subject}")

        time.sleep(SLEEP_BETWEEN)

    except smtplib.SMTPServerDisconnected:
        log("SMTP disconnected. Reconnecting...")
        smtp = connect_smtp()

    except Exception as e:
        log(f"[{i}] Failed to forward: {e}")

log("=" * 60)
log("Run complete.")
log("=" * 60)

smtp.quit()
imap.logout()

#!/usr/bin/env python3
import imaplib
import smtplib
import email
from email.message import EmailMessage
import os
import logging
from datetime import datetime

# =======================
# CONFIG & ENV VARIABLES
# =======================
YAHOO_EMAIL = os.environ.get("YAHOO_EMAIL")
YAHOO_APP_PASSWORD = os.environ.get("YAHOO_APP_PASSWORD")
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
MAX_EMAILS = 50  # How many unread emails to process per run

# =======================
# LOGGING SETUP
# =======================
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# =======================
# HELPER FUNCTIONS
# =======================
def connect_imap():
    logging.info("Connecting to Yahoo IMAP...")
    imap = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
    imap.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
    imap.select("INBOX")
    logging.info("✓ Connected to Yahoo IMAP")
    return imap

def connect_smtp():
    logging.info("Connecting to Gmail SMTP...")
    smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
    logging.info("✓ Connected to Gmail SMTP")
    return smtp

def fetch_unread_emails(imap):
    status, response = imap.search(None, "UNSEEN")
    if status != "OK":
        logging.error("Failed to fetch unread emails")
        return []
    email_ids = response[0].split()
    return email_ids[:MAX_EMAILS]

def forward_email(smtp, raw_email):
    msg = email.message_from_bytes(raw_email)

    forward_msg = EmailMessage()
    # Set subject and from/to headers
    subject = msg.get("Subject", "(no subject)")
    # Remove problematic linebreaks
    subject = "".join(subject.splitlines())
    forward_msg["Subject"] = f"FWD: {subject}"
    forward_msg["From"] = GMAIL_EMAIL
    forward_msg["To"] = GMAIL_EMAIL

    # Handle the email body (plain text or HTML)
    body_bytes = None
    if msg.is_multipart():
        # Prefer HTML if available
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                body_bytes = part.get_payload(decode=True)
                break
            elif content_type == "text/plain" and body_bytes is None:
                body_bytes = part.get_payload(decode=True)
    else:
        body_bytes = msg.get_payload(decode=True)

    if body_bytes is None:
        body_bytes = b"(No content)"

    # ✅ FIX FOR PYTHON 3.11+
    if isinstance(body_bytes, str):
        body_bytes = body_bytes.encode("utf-8")
    forward_msg.set_bytes_content(body_bytes)

    # Send email
    smtp.send_message(forward_msg)

# =======================
# MAIN FUNCTION
# =======================
def main():
    # Check required environment variables
    missing_envs = [v for v in ["YAHOO_EMAIL", "YAHOO_APP_PASSWORD", "GMAIL_EMAIL", "GMAIL_APP_PASSWORD"]
                    if os.environ.get(v) is None]
    if missing_envs:
        logging.error(f"Missing environment variables: {', '.join(missing_envs)}")
        return

    logging.info("="*60)
    logging.info("Starting robust Yahoo → Gmail forwarder")
    logging.info(f"Yahoo: {YAHOO_EMAIL} → Gmail: {GMAIL_EMAIL}")
    logging.info("="*60)

    try:
        imap = connect_imap()
        smtp = connect_smtp()
    except Exception as e:
        logging.error(f"Connection error: {e}")
        return

    try:
        email_ids = fetch_unread_emails(imap)
        total = len(email_ids)
        logging.info(f"Found {total} unread; processing {total}")

        for i, eid in enumerate(email_ids, start=1):
            try:
                status, data = imap.fetch(eid, "(RFC822)")
                if status != "OK":
                    logging.error(f"[{i}/{total}] Failed to fetch email id {eid.decode()}")
                    continue
                raw_email = data[0][1]
                forward_email(smtp, raw_email)
                logging.info(f"[{i}/{total}] Forwarded: {email.message_from_bytes(raw_email).get('Subject')}")
            except Exception as e:
                logging.error(f"[{i}/{total}] Error forwarding: {e}")

    finally:
        try:
            smtp.quit()
        except:
            pass
        try:
            imap.logout()
        except:
            pass

    logging.info("="*60)
    logging.info(f"Summary: Total unread: {total}, Forwarded: {total}, Failed: TBD")
    logging.info("="*60)

if __name__ == "__main__":
    main()

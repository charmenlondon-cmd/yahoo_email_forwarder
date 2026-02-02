#!/usr/bin/env python3

import imaplib
import smtplib
import os
import email
from email.message import EmailMessage
from datetime import datetime
import time
import sys

YAHOO_EMAIL = os.environ.get("YAHOO_EMAIL")
YAHOO_APP_PASSWORD = os.environ.get("YAHOO_APP_PASSWORD")
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")

IMAP_SERVER = "imap.mail.yahoo.com"
SMTP_SERVER = "smtp.mail.yahoo.com"
SMTP_PORT = 465

MAX_PER_RUN = 50
DELAY_BETWEEN_EMAILS = 2


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def validate():
    if not YAHOO_EMAIL or not YAHOO_APP_PASSWORD or not GMAIL_EMAIL:
        log("Missing required environment variables.")
        sys.exit(1)


def connect_imap():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
    mail.select("INBOX")
    return mail


def connect_smtp():
    smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
    smtp.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
    return smtp


def main():
    validate()

    log("=" * 60)
    log("Starting Yahoo → Gmail forwarder")
    log("=" * 60)

    mail = connect_imap()
    smtp = connect_smtp()

    status, data = mail.search(None, "UNSEEN")
    email_ids = data[0].split()

    if not email_ids:
        log("No unread emails found.")
        return

    total = len(email_ids)
    batch = email_ids[:MAX_PER_RUN]

    log(f"Found {total} unread emails")
    log(f"Processing {len(batch)} this run")

    for i, eid in enumerate(batch, 1):
        try:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            raw_email = msg_data[0][1]
            original_msg = email.message_from_bytes(raw_email)

            original_subject = original_msg.get("Subject", "")
            original_from = original_msg.get("From", "")

            # Clean subject (remove newlines to avoid header errors)
            clean_subject = original_subject.replace("\n", " ").replace("\r", " ")

            fwd = EmailMessage()
            fwd["From"] = YAHOO_EMAIL
            fwd["To"] = GMAIL_EMAIL
            fwd["Subject"] = f"FWD: {clean_subject}"

            body = f"""Forwarded message:

From: {original_from}
Subject: {original_subject}

Original email is attached as .eml file.
"""

            fwd.set_content(body)

            # Attach original email safely
            fwd.add_attachment(
                raw_email,
                maintype="message",
                subtype="rfc822",
                filename="original_message.eml"
            )

            smtp.send_message(fwd)

            # Mark as read ONLY after successful send
            mail.store(eid, "+FLAGS", "\\Seen")

            log(f"[{i}/{len(batch)}] Forwarded: {clean_subject}")

            time.sleep(DELAY_BETWEEN_EMAILS)

        except Exception as e:
            log(f"[{i}] Failed to forward: {e}")

    try:
        smtp.quit()
    except:
        pass

    mail.logout()

    log("=" * 60)
    log("Run complete.")
    log("=" * 60)


if __name__ == "__main__":
    main()

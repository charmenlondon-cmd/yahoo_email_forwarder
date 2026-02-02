#!/usr/bin/env python3
"""
Yahoo → Gmail Email Forwarder (Robust Version)
Fetches unread emails from Yahoo IMAP, rebuilds them safely, and forwards via Yahoo SMTP.
Marks emails as read in Yahoo. Keeps Gmail Inbox clean.
"""

import imaplib
import email
from email.message import EmailMessage
import smtplib
import os
import sys
from datetime import datetime
import time

# Credentials from GitHub Secrets
YAHOO_EMAIL = os.environ.get('YAHOO_EMAIL')
YAHOO_APP_PASSWORD = os.environ.get('YAHOO_APP_PASSWORD')
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL')

# Settings
MAX_EMAILS_PER_RUN = 50
DELAY_BETWEEN_EMAILS = 2  # seconds

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def validate_credentials():
    missing = [name for name, val in {
        'YAHOO_EMAIL': YAHOO_EMAIL,
        'YAHOO_APP_PASSWORD': YAHOO_APP_PASSWORD,
        'GMAIL_EMAIL': GMAIL_EMAIL
    }.items() if not val]
    if missing:
        log(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

def fetch_and_forward():
    validate_credentials()
    try:
        log("="*60)
        log("Starting robust Yahoo → Gmail forwarder")
        log(f"Yahoo: {YAHOO_EMAIL} → Gmail: {GMAIL_EMAIL}")

        # Connect to Yahoo IMAP
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        mail.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
        mail.select('inbox')
        log("Connected to Yahoo IMAP")

        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        if not email_ids:
            log("No unread emails")
            mail.close()
            mail.logout()
            return

        total_unread = len(email_ids)
        email_ids_to_process = email_ids[:MAX_EMAILS_PER_RUN]
        log(f"Found {total_unread} unread, processing {len(email_ids_to_process)}")

        # Connect to Yahoo SMTP
        smtp = smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465)
        smtp.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
        log("Connected to Yahoo SMTP")

        forwarded = 0
        failed = 0

        for i, num in enumerate(email_ids_to_process, 1):
            try:
                # Fetch the email
                status, msg_data = mail.fetch(num, '(RFC822)')
                original_email = email.message_from_bytes(msg_data[0][1])

                # Build new EmailMessage for robust forwarding
                fwd_email = EmailMessage()
                fwd_email['From'] = YAHOO_EMAIL
                fwd_email['To'] = GMAIL_EMAIL
                fwd_email['Subject'] = original_email.get('Subject', 'No Subject')

                # Copy plain text and HTML body
                if original_email.is_multipart():
                    for part in original_email.walk():
                        content_type = part.get_content_type()
                        if content_type in ['text/plain', 'text/html']:
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or 'utf-8'
                            if content_type == 'text/plain':
                                fwd_email.set_content(payload.decode(charset, errors='ignore'))
                            else:
                                fwd_email.add_alternative(payload.decode(charset, errors='ignore'), subtype='html')
                        elif part.get('Content-Disposition') and 'attachment' in part.get('Content-Disposition'):
                            fwd_email.add_attachment(part.get_payload(decode=True),
                                                     maintype=part.get_content_maintype(),
                                                     subtype=part.get_content_subtype(),
                                                     filename=part.get_filename())
                else:
                    payload = original_email.get_payload(decode=True)
                    charset = original_email.get_content_charset() or 'utf-8'
                    fwd_email.set_content(payload.decode(charset, errors='ignore'))

                # Send via Yahoo SMTP
                smtp.send_message(fwd_email)

                # Mark original email as read
                mail.store(num, '+FLAGS', '\\Seen')

                forwarded += 1
                log(f"[{i}/{len(email_ids_to_process)}] Forwarded: {fwd_email['Subject']}")

                if i < len(email_ids_to_process):
                    time.sleep(DELAY_BETWEEN_EMAILS)

            except Exception as e:
                failed += 1
                log(f"[{i}] Error: {str(e)}")
                continue

        # Cleanup
        smtp.quit()
        mail.close()
        mail.logout()

        log("="*60)
        log(f"Summary: Total unread: {total_unread}, Forwarded: {forwarded}, Failed: {failed}")
        log("="*60)

    except Exception as e:
        import traceback
        log(f"Unexpected error: {str(e)}")
        log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_forward()

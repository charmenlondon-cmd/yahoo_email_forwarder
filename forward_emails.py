#!/usr/bin/env python3
import imaplib
import email
from email.message import EmailMessage
import smtplib
import os
import logging

# -----------------------
# CONFIGURATION
# -----------------------
YAHOO_EMAIL = os.environ.get("YAHOO_EMAIL")
YAHOO_PASSWORD = os.environ.get("YAHOO_PASSWORD")
GMAIL_EMAIL = os.environ.get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")

if not all([YAHOO_EMAIL, YAHOO_PASSWORD, GMAIL_EMAIL, GMAIL_APP_PASSWORD]):
    raise ValueError("Missing one or more environment variables: YAHOO_EMAIL, YAHOO_PASSWORD, GMAIL_EMAIL, GMAIL_APP_PASSWORD")

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# -----------------------
# CONNECT TO YAHOO IMAP
# -----------------------
logging.info("Connecting to Yahoo IMAP...")
imap = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
imap.login(YAHOO_EMAIL, YAHOO_PASSWORD)
imap.select("INBOX")
logging.info("✓ Connected to Yahoo IMAP")

# -----------------------
# CONNECT TO GMAIL SMTP
# -----------------------
logging.info("Connecting to Gmail SMTP...")
smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
logging.info("✓ Connected to Gmail SMTP")

# -----------------------
# FETCH UNREAD EMAILS
# -----------------------
status, messages = imap.search(None, "UNSEEN")
email_ids = messages[0].split()
logging.info(f"Found {len(email_ids)} unread; processing up to 50")
email_ids = email_ids[:50]

# -----------------------
# FORWARD EMAILS
# -----------------------
for idx, e_id in enumerate(email_ids, start=1):
    try:
        _, msg_data = imap.fetch(e_id, "(RFC822)")
        raw_email = msg_data[0][1]
        original_msg = email.message_from_bytes(raw_email)

        # Create new message
        fwd_msg = EmailMessage()
        fwd_msg['Subject'] = "FWD: " + original_msg.get('Subject', '')
        fwd_msg['From'] = GMAIL_EMAIL
        fwd_msg['To'] = GMAIL_EMAIL  # Forwarding to yourself
        fwd_msg['Reply-To'] = original_msg.get('From')

        # Handle plain text and HTML
        if original_msg.is_multipart():
            for part in original_msg.walk():
                content_type = part.get_content_type()
                disposition = part.get_content_disposition()
                charset = part.get_content_charset() or "utf-8"

                if disposition == "attachment":
                    fwd_msg.add_attachment(part.get_payload(decode=True),
                                           maintype=part.get_content_maintype(),
                                           subtype=part.get_content_subtype(),
                                           filename=part.get_filename())
                elif content_type == "text/plain":
                    fwd_msg.set_content(part.get_payload(decode=True).decode(charset, errors='replace'))
                elif content_type == "text/html":
                    fwd_msg.add_alternative(part.get_payload(decode=True).decode(charset, errors='replace'), subtype='html')
        else:
            # Single part message
            charset = original_msg.get_content_charset() or "utf-8"
            fwd_msg.set_content(original_msg.get_payload(decode=True).decode(charset, errors='replace'))

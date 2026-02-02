#!/usr/bin/env python3
import os
import imaplib
import email
import smtplib
from email.message import EmailMessage
from email.policy import default

# Environment variables
YAHOO_EMAIL = os.environ['YAHOO_EMAIL']
YAHOO_APP_PASSWORD = os.environ['YAHOO_APP_PASSWORD']
GMAIL_EMAIL = os.environ['GMAIL_EMAIL']
GMAIL_APP_PASSWORD = os.environ['GMAIL_APP_PASSWORD']

# IMAP / SMTP settings
YAHOO_IMAP = 'imap.mail.yahoo.com'
GMAIL_SMTP = 'smtp.gmail.com'
GMAIL_SMTP_PORT = 587

def fetch_unread_yahoo():
    mail = imaplib.IMAP4_SSL(YAHOO_IMAP)
    mail.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
    mail.select('INBOX')
    typ, data = mail.search(None, 'UNSEEN')
    mail_ids = data[0].split()
    messages = []
    for num in mail_ids:
        typ, msg_data = mail.fetch(num, '(RFC822)')
        raw_email = msg_data[0][1]
        messages.append(email.message_from_bytes(raw_email, policy=default))
    mail.logout()
    return messages

def forward_to_gmail(original_msg):
    fwd_msg = EmailMessage()
    fwd_msg['Subject'] = original_msg['Subject']
    fwd_msg['From'] = GMAIL_EMAIL
    fwd_msg['To'] = GMAIL_EMAIL  # forward to self, adjust if needed

    if original_msg.is_multipart():
        for part in original_msg.walk():
            content_type = part.get_content_type()
            content_disposition = part.get_content_disposition()
            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True)

            if payload is None:
                continue

            if content_disposition == 'attachment':
                fwd_msg.add_attachment(payload, maintype=part.get_content_maintype(),
                                       subtype=part.get_content_subtype(),
                                       filename=part.get_filename())
            else:
                if content_type == 'text/plain':
                    fwd_msg.set_content(payload.decode(charset, errors='replace'))
                elif content_type == 'text/html':
                    fwd_msg.add_alternative(payload.decode(charset, errors='replace'), subtype='html')
    else:
        # Single part message
        charset = original_msg.get_content_charset() or "utf-8"
        fwd_msg.set_content(original_msg.get_payload(decode=True).decode(charset, errors='replace'))

    # Send via Gmail SMTP
    with smtplib.SMTP(GMAIL_SMTP, GMAIL_SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        smtp.send_message(fwd_msg)

def main():
    print("="*60)
    print(f"Starting robust Yahoo → Gmail forwarder")
    print(f"Yahoo: {YAHOO_EMAIL} → Gmail: {GMAIL_EMAIL}")
    print("="*60)
    messages = fetch_unread_yahoo()
    print(f"Found {len(messages)} unread messages; processing all")
    success, failed = 0, 0
    for i, msg in enumerate(messages, 1):
        try:
            forward_to_gmail(msg)
            print(f"[{i}/{len(messages)}] Forwarded successfully")
            success += 1
        except Exception as e:
            print(f"[{i}/{len(messages)}] Error forwarding: {e}")
            failed += 1
    print("="*60)
    print(f"Summary: Total unread: {len(messages)}, Forwarded: {success}, Failed: {failed}")
    print("="*60)

if __name__ == "__main__":
    main()

import imaplib
import smtplib
import email
from email.message import EmailMessage
import os

# Environment variables
YAHOO_EMAIL = os.environ['YAHOO_EMAIL']
YAHOO_APP_PASSWORD = os.environ['YAHOO_APP_PASSWORD']
GMAIL_EMAIL = os.environ['GMAIL_EMAIL']
GMAIL_APP_PASSWORD = os.environ['GMAIL_APP_PASSWORD']

# Connect to Yahoo IMAP
imap = imaplib.IMAP4_SSL('imap.mail.yahoo.com')
imap.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
imap.select('INBOX')

# Search for unread emails
status, messages = imap.search(None, 'UNSEEN')
email_ids = messages[0].split()

# Connect to Gmail SMTP
smtp = smtplib.SMTP_SSL('smtp.gmail.com', 465)
smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)

for i, email_id in enumerate(email_ids, start=1):
    status, msg_data = imap.fetch(email_id, '(RFC822)')
    raw_email = msg_data[0][1]
    original_msg = email.message_from_bytes(raw_email)

    # Forward email
    fwd_msg = EmailMessage()
    fwd_msg['From'] = GMAIL_EMAIL
    fwd_msg['To'] = GMAIL_EMAIL  # change if forwarding elsewhere
    fwd_msg['Subject'] = f"FWD: {original_msg.get('Subject', '')}"

    # Simply copy the raw payload
    if original_msg.is_multipart():
        fwd_msg.set_content("This is a forwarded multipart email. See attachment for full content.")
        for part in original_msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            fwd_msg.add_attachment(part.get_payload(decode=True),
                                   maintype=part.get_content_maintype(),
                                   subtype=part.get_content_subtype(),
                                   filename=part.get_filename())
    else:
        fwd_msg.set_content(original_msg.get_payload(decode=True), subtype='plain')

    try:
        smtp.send_message(fwd_msg)
        print(f"[{i}/{len(email_ids)}] Forwarded successfully")
    except Exception as e:
        print(f"[{i}/{len(email_ids)}] Failed to forward: {e}")

# Close connections
imap.logout()
smtp.quit()
print("Done forwarding all emails.")

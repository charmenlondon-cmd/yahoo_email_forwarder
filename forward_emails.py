#!/usr/bin/env python3
"""
Robust Yahoo → Gmail Email Forwarder
Fetches unread emails from Yahoo and forwards them to Gmail, properly handling HTML & plain text.
"""

import imaplib
import email
from email.message import EmailMessage
import smtplib
import os
import sys
from datetime import datetime
import time

# --------------------------
# Configuration / Secrets
# --------------------------
YAHOO_EMAIL = os.environ.get('YAHOO_EMAIL')
YAHOO_APP_PASSWORD = os.environ.get('YAHOO_APP_PASSWORD')
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

MAX_EMAILS_PER_RUN = 50
DELAY_BETWEEN_EMAILS = 2  # seconds

# --------------------------
# Logging
# --------------------------
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# --------------------------
# Credential check
# --------------------------
def validate_credentials():
    required = {
        'YAHOO_EMAIL': YAHOO_EMAIL,
        'YAHOO_APP_PASSWORD': YAHOO_APP_PASSWORD,
        'GMAIL_EMAIL': GMAIL_EMAIL,
        'GMAIL_APP_PASSWORD': GMAIL_APP_PASSWORD
    }
    missing = [k for k,v in required.items() if not v]
    if missing:
        log(f"ERROR: Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

# --------------------------
# Forwarding
# --------------------------
def forward_email(yahoo_msg, smtp_conn):
    """
    Create a clean email message to Gmail, preserving HTML/plain text content.
    """
    new_msg = EmailMessage()
    from_addr = YAHOO_EMAIL
    to_addr = GMAIL_EMAIL
    subject = yahoo_msg.get('Subject', 'No Subject')
    
    # Clean subject to remove newlines
    subject = ' '.join(subject.splitlines())
    
    new_msg['From'] = from_addr
    new_msg['To'] = to_addr
    new_msg['Subject'] = f"Fwd: {subject}"
    
    # Preserve original plain text and HTML content
    if yahoo_msg.is_multipart():
        for part in yahoo_msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain' and part.get_content_disposition() in (None, 'inline'):
                new_msg.set_content(part.get_payload(decode=True), subtype='plain', charset=part.get_content_charset())
            elif content_type == 'text/html' and part.get_content_disposition() in (None, 'inline'):
                new_msg.add_alternative(part.get_payload(decode=True), subtype='html', charset=part.get_content_charset())
    else:
        ctype = yahoo_msg.get_content_type()
        if ctype == 'text/plain':
            new_msg.set_content(yahoo_msg.get_payload(decode=True), subtype='plain', charset=yahoo_msg.get_content_charset())
        elif ctype == 'text/html':
            new_msg.add_alternative(yahoo_msg.get_payload(decode=True), subtype='html', charset=yahoo_msg.get_content_charset())
    
    smtp_conn.send_message(new_msg)

# --------------------------
# Main processing
# --------------------------
def fetch_and_forward():
    validate_credentials()
    try:
        log("="*60)
        log("Starting robust Yahoo → Gmail forwarder")
        log(f"Yahoo: {YAHOO_EMAIL} → Gmail: {GMAIL_EMAIL}")
        log("="*60)
        
        # Connect to Yahoo IMAP
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        mail.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
        mail.select("inbox")
        log("✓ Connected to Yahoo IMAP")
        
        # Search for unread emails
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        if not email_ids:
            log("No unread emails found")
            mail.close()
            mail.logout()
            return
        
        total_unread = len(email_ids)
        to_process = email_ids[:MAX_EMAILS_PER_RUN]
        log(f"Found {total_unread} unread; processing {len(to_process)}")
        
        # Connect to Gmail SMTP
        smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        log("✓ Connected to Gmail SMTP")
        
        forwarded_count = 0
        failed_count = 0
        
        for i, eid in enumerate(to_process, 1):
            try:
                status, msg_data = mail.fetch(eid, '(RFC822)')
                yahoo_msg = email.message_from_bytes(msg_data[0][1])
                
                forward_email(yahoo_msg, smtp)
                
                # Mark as read in Yahoo
                mail.store(eid, '+FLAGS', '\\Seen')
                
                forwarded_count += 1
                log(f"[{i}/{len(to_process)}] Forwarded: {yahoo_msg.get('Subject','No Subject')}")
                
                if i < len(to_process):
                    time.sleep(DELAY_BETWEEN_EMAILS)
                    
            except Exception as e:
                failed_count += 1
                log(f"[{i}/{len(to_process)}] Error forwarding: {str(e)}")
        
        smtp.quit()
        mail.close()
        mail.logout()
        
        log("="*60)
        log(f"Summary: Total unread: {total_unread}, Forwarded: {forwarded_count}, Failed: {failed_count}")
        if total_unread > len(to_process):
            log(f"Remaining for next run: {total_unread - len(to_process)}")
        log("="*60)
        
    except Exception as e:
        log(f"Unexpected error: {str(e)}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_forward()

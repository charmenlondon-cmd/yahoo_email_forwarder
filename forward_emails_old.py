#!/usr/bin/env python3
"""
Yahoo to Gmail Email Forwarder
Fetches unread emails from Yahoo and forwards them to Gmail
"""

import imaplib
import email
import smtplib
import os
import sys
from datetime import datetime

# Get credentials from GitHub Secrets (environment variables)
YAHOO_EMAIL = os.environ.get('YAHOO_EMAIL')
YAHOO_APP_PASSWORD = os.environ.get('YAHOO_APP_PASSWORD')
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Settings
MAX_EMAILS_PER_RUN = 50  # Process max 50 emails per run
DELAY_BETWEEN_EMAILS = 2  # 2 seconds between each forward

def log(message):
    """Print log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def validate_credentials():
    """Check that all required credentials are set"""
    required = {
        'YAHOO_EMAIL': YAHOO_EMAIL,
        'YAHOO_APP_PASSWORD': YAHOO_APP_PASSWORD,
        'GMAIL_EMAIL': GMAIL_EMAIL,
        'GMAIL_APP_PASSWORD': GMAIL_APP_PASSWORD
    }
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        log(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        log("Please set these as GitHub Secrets in your repository settings")
        sys.exit(1)

def fetch_and_forward():
    """Fetch unread emails from Yahoo and forward to Gmail"""
    
    # Validate credentials first
    validate_credentials()
    
    try:
        log("=" * 60)
        log("Starting Yahoo to Gmail email forwarder")
        log("=" * 60)
        log(f"Yahoo account: {YAHOO_EMAIL}")
        log(f"Gmail account: {GMAIL_EMAIL}")
        log("")
        
        # Connect to Yahoo IMAP
        log("Connecting to Yahoo IMAP...")
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        mail.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
        mail.select('inbox')
        log("✓ Connected to Yahoo successfully")
        
        # Search for unread emails
        log("Searching for unread emails...")
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        if not email_ids:
            log("No unread emails found")
            log("=" * 60)
            mail.close()
            mail.logout()
            return
        
        total_unread = len(email_ids)
        log(f"Found {total_unread} unread email(s)")
        
        # Limit processing to MAX_EMAILS_PER_RUN
        email_ids_to_process = email_ids[:MAX_EMAILS_PER_RUN]
        processing_count = len(email_ids_to_process)
        
        if total_unread > MAX_EMAILS_PER_RUN:
            log(f"Will process {processing_count} emails this run (max limit)")
            log(f"Remaining {total_unread - processing_count} will be processed in next run")
        else:
            log(f"Processing all {processing_count} email(s)")
        
        log("")
        
        # Connect to Gmail SMTP
        log("Connecting to Gmail SMTP...")
        smtp = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        smtp.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
        log("✓ Connected to Gmail successfully")
        log("")
        
        forwarded_count = 0
        failed_count = 0
        
        for i, num in enumerate(email_ids_to_process, 1):
            try:
                # Fetch email
                status, msg_data = mail.fetch(num, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                # Get email details for logging
                subject = email_message.get('Subject', 'No Subject')
                from_addr = email_message.get('From', 'Unknown')
                
                # Truncate subject if too long
                if len(subject) > 60:
                    subject = subject[:57] + "..."
                
                log(f"[{i}/{processing_count}] Forwarding:")
                log(f"  From: {from_addr}")
                log(f"  Subject: {subject}")
                
                # Forward to Gmail
                smtp.send_message(email_message, YAHOO_EMAIL, GMAIL_EMAIL)
                
                # Mark as read in Yahoo
                mail.store(num, '+FLAGS', '\\Seen')
                
                forwarded_count += 1
                log(f"  ✓ Forwarded successfully")
                
                # Small delay between emails to be nice to servers
                if i < processing_count:
                    import time
                    time.sleep(DELAY_BETWEEN_EMAILS)
                
            except Exception as e:
                failed_count += 1
                log(f"  ✗ Error forwarding email: {str(e)}")
                # Continue with next email
        
        # Cleanup
        smtp.quit()
        mail.close()
        mail.logout()
        
        log("")
        log("=" * 60)
        log(f"Summary:")
        log(f"  Total unread emails: {total_unread}")
        log(f"  Successfully forwarded: {forwarded_count}")
        if failed_count > 0:
            log(f"  Failed: {failed_count}")
        if total_unread > processing_count:
            log(f"  Remaining for next run: {total_unread - processing_count}")
        log("=" * 60)
        
    except imaplib.IMAP4.error as e:
        log(f"ERROR: IMAP connection failed: {str(e)}")
        log("Check your Yahoo email and app password")
        sys.exit(1)
    except smtplib.SMTPException as e:
        log(f"ERROR: SMTP connection failed: {str(e)}")
        log("Check your Gmail email and app password")
        sys.exit(1)
    except Exception as e:
        log(f"ERROR: Unexpected error: {str(e)}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_forward()

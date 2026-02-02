#!/usr/bin/env python3
"""
Robust Yahoo → Gmail Email Forwarder
- Fetches unread emails from Yahoo IMAP
- Forwards via Yahoo SMTP to Gmail
- Marks emails as read in Yahoo
- Sanitizes headers to prevent SMTP errors
- Handles multipart emails and attachments
- Wraps SMTP sends in try/except to continue on errors
- Reconnects SMTP if disconnected mid-run
"""

import imaplib
import email
from email.message import EmailMessage
import smtplib
import os
import sys
import time
from datetime import datetime

# Environment variables (GitHub Secrets)
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

def sanitize_header(value):
    """Remove newlines/carriage returns from headers to prevent SMTP errors"""
    if value:
        return value.replace('\n', ' ').replace('\r', ' ')
    return value

def connect_smtp():
    """Connect to Yahoo SMTP and return SMTP object"""
    smtp_conn = smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465)
    smtp_conn.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
    log("Connected to Yahoo SMTP")
    return smtp_conn

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
        log(f"Found {total_u_

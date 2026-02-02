#!/usr/bin/env python3
"""
Yahoo → Gmail Email Forwarder (Robust Version with SMTP quit fix)
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
        log(f"ERROR: Missing environment variables: {', '.join(missin

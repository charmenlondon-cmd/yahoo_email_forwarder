#!/usr/bin/env python3
"""
Yahoo to Gmail Email Forwarder
Fetches unread emails from Yahoo and forwards them to Gmail
Runs only between 00:01-09:00 system time, max 9 runs/day (450 emails)
"""

import imaplib
import email
import smtplib
import os
import sys
import json
from datetime import datetime, time
from pathlib import Path

# Get credentials from GitHub Secrets (environment variables)
YAHOO_EMAIL = os.environ.get('YAHOO_EMAIL')
YAHOO_APP_PASSWORD = os.environ.get('YAHOO_APP_PASSWORD')
GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')

# Settings
MAX_EMAILS_PER_RUN = 50  # Process max 50 emails per run
MAX_RUNS_PER_DAY = 9     # Run 9 times per day max (450 emails total)
DELAY_BETWEEN_EMAILS = 2  # 2 seconds between each forward

# Time window settings (system time)
RUN_START_TIME = time(0, 1)   # 00:01
RUN_END_TIME = time(9, 0)     # 09:00

# File to track daily runs
COUNTER_FILE = Path("/tmp/gmail_daily_runs.json")

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

def is_within_run_window():
    """Check if current time is within the allowed run window"""
    current_time = datetime.now().time()
    return RUN_START_TIME <= current_time <= RUN_END_TIME

def get_daily_run_count():
    """Get today's run count from counter file"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    if not COUNTER_FILE.exists():
        return 0, 0, today
    
    try:
        with open(COUNTER_FILE, 'r') as f:
            data = json.load(f)
        
        # If it's a new day, reset counter
        if data.get('date') != today:
            return 0, 0, today
        
        return data.get('runs', 0), data.get('emails_sent', 0), today
    except:
        return 0, 0, today

def update_daily_run_count(runs, emails_sent, date):
    """Update the daily run counter file"""
    try:
        with open(COUNTER_FILE, 'w') as f:
            json.dump({
                'date': date, 
                'runs': runs,
                'emails_sent': emails_sent
            }, f)
    except Exception as e:
        log(f"Warning: Could not update counter file: {e}")

def fetch_and_forward():
    """Fetch unread emails from Yahoo and forward to Gmail"""
    
    # Validate credentials first
    validate_credentials()
    
    # Check if we're within the allowed time window
    current_time_str = datetime.now().strftime("%H:%M:%S")
    
    if not is_within_run_window():
        log("=" * 60)
        log("Outside allowed run window")
        log(f"Current time: {current_time_str}")
        log(f"Allowed window: 00:01 - 09:00")
        log("Script will run during the next allowed window")
        log("=" * 60)
        return
    
    # Check daily run count
    runs_today, emails_sent_today, today = get_daily_run_count()
    runs_remaining = MAX_RUNS_PER_DAY - runs_today
    max_emails_today = MAX_RUNS_PER_DAY * MAX_EMAILS_PER_RUN
    
    try:
        log("=" * 60)
        log("Starting Yahoo to Gmail email forwarder")
        log("=" * 60)
        log(f"Yahoo account: {YAHOO_EMAIL}")
        log(f"Gmail account: {GMAIL_EMAIL}")
        log(f"Date: {today}")
        log(f"Time: {current_time_str}")
        log(f"Run: {runs_today + 1}/{MAX_RUNS_PER_DAY}")
        log(f"Emails sent today: {emails_sent_today}/{max_emails_today}")
        log("")
        
        # Check if we've hit the daily run limit
        if runs_today >= MAX_RUNS_PER_DAY:
            log("⚠ Daily run limit reached!")
            log(f"Already completed {runs_today} runs today (max: {MAX_RUNS_PER_DAY})")
            log(f"Total emails forwarded today: {emails_sent_today}")
            log("Will resume tomorrow at 00:01")
            log("=" * 60)
            return
        
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
        
        # Process up to MAX_EMAILS_PER_RUN
        email_ids_to_process = email_ids[:MAX_EMAILS_PER_RUN]
        processing_count = len(email_ids_to_process)
        
        log(f"Will process {processing_count} email(s) this run")
        if total_unread > processing_count:
            log(f"Remaining {total_unread - processing_count} will be processed in next run")
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
                
                # Small delay between emails
                if i < processing_count:
                    import time
                    time.sleep(DELAY_BETWEEN_EMAILS)
                
            except Exception as e:
                failed_count += 1
                log(f"  ✗ Error forwarding email: {str(e)}")
                # Continue with next email
        
        # Update counters
        runs_today += 1
        emails_sent_today += forwarded_count
        update_daily_run_count(runs_today, emails_sent_today, today)
        
        # Cleanup
        smtp.quit()
        mail.close()
        mail.logout()
        
        log("")
        log("=" * 60)
        log(f"Summary:")
        log(f"  Run {runs_today}/{MAX_RUNS_PER_DAY} complete")
        log(f"  Total unread emails: {total_unread}")
        log(f"  Successfully forwarded this run: {forwarded_count}")
        log(f"  Total sent today: {emails_sent_today}/{max_emails_today}")
        if failed_count > 0:
            log(f"  Failed: {failed_count}")
        if runs_today >= MAX_RUNS_PER_DAY:
            log(f"  ⚠ Daily limit reached - will resume tomorrow at 00:01")
        elif total_unread > processing_count:
            remaining_runs = MAX_RUNS_PER_DAY - runs_today
            log(f"  Remaining runs today: {remaining_runs}")
            log(f"  Can process up to {remaining_runs * MAX_EMAILS_PER_RUN} more emails today")
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

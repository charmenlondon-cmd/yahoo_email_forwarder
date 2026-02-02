import imaplib
import smtplib
import email
import os
import ssl

# ==============================
# CONFIG FROM ENV VARIABLES
# ==============================

YAHOO_EMAIL = os.environ["YAHOO_EMAIL"]
YAHOO_APP_PASSWORD = os.environ["YAHOO_APP_PASSWORD"]
GMAIL_EMAIL = os.environ["GMAIL_EMAIL"]

IMAP_SERVER = "imap.mail.yahoo.com"
SMTP_SERVER = "smtp.mail.yahoo.com"
SMTP_PORT = 465  # SSL

BATCH_LIMIT = 50  # prevent overload

print("============================================================")
print("Starting Yahoo → Gmail forwarder")
print("============================================================")

# ==============================
# CONNECT TO YAHOO IMAP
# ==============================

mail = imaplib.IMAP4_SSL(IMAP_SERVER)
mail.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)
mail.select("INBOX")

status, messages = mail.search(None, "UNSEEN")
email_ids = messages[0].split()

total_unread = len(email_ids)
print(f"Found {total_unread} unread emails")

if total_unread == 0:
    print("Nothing to forward.")
    mail.logout()
    exit()

email_ids = email_ids[:BATCH_LIMIT]

# ==============================
# CONNECT TO YAHOO SMTP
# ==============================

context = ssl.create_default_context()
smtp = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
smtp.login(YAHOO_EMAIL, YAHOO_APP_PASSWORD)

forwarded = 0

# ==============================
# PROCESS EMAILS
# ==============================

for i, email_id in enumerate(email_ids, start=1):
    try:
        status, msg_data = mail.fetch(email_id, "(RFC822)")
        raw_email = msg_data[0][1]

        original_msg = email.message_from_bytes(raw_email)

        # Send raw email directly from Yahoo to Gmail
        smtp.sendmail(
            YAHOO_EMAIL,
            GMAIL_EMAIL,
            raw_email
        )

        # Mark as seen so it doesn't resend
        mail.store(email_id, "+FLAGS", "\\Seen")

        forwarded += 1
        print(f"[{i}/{len(email_ids)}] Forwarded: {original_msg.get('Subject')}")

    except Exception as e:
        print(f"[{i}] Failed to forward:", e)

# ==============================
# CLEANUP
# ==============================

smtp.quit()
mail.logout()

print("============================================================")
print(f"Forwarded {forwarded} of {len(email_ids)} emails")
print("============================================================")

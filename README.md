# yahoo_email_forwarder

Runs every hour. Gets Gmail to effectively send the yahoo inbox emails from itself to itself (hence you will find all the inbox emails in the outbox as well)
At the moment (06/02/2026) it is running a capped version which sends a max of 450 emails a day, since there are a load of unread emails to clear from yahoo, but once those are done, I will switch to the supernew code which will do what point 1 says.
When switching to the supernew code - I must remember to change the Github actions workflow to run every hour (if not already set to that) as follows
schedule:
  - cron: '0 * * * *'  # Every hour on the hour

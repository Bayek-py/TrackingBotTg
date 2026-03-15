━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ANONXPRESS TRACKING SYSTEM — SETUP
  AU & USA Internal Shipping Network
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW IT WORKS
━━━━━━━━━━━━
  bot.py      — Telegram bot (admin manages parcels)
  server.py   — Local API server (feeds the website tracking page)
  parcels.json — Shared data file between both

  Flow:
  1. You add a parcel via Telegram → saved to parcels.json
  2. server.py reads parcels.json and serves it on localhost:8080
  3. When a customer enters an ANX- number on the website,
     the site fetches from server.py and shows live tracking

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 1 — Install Python (if not already)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Download from https://python.org
  Make sure to tick "Add Python to PATH" during install

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 2 — Install dependencies
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open terminal in this folder and run:

    pip install -r requirements.txt

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 3 — Start everything
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Double-click START_BOT.bat

  This launches TWO windows:
    - AnonXpress Tracking Server (server.py on port 8080)
    - AnonXpress Telegram Bot    (bot.py)

  Keep BOTH windows open while operating.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  STEP 4 — Register yourself as admin
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Open the bot on Telegram and send:

    /setupadmin

  Do this ONCE. Your Telegram ID is saved as admin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO USE — ADMIN COMMANDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Add a new parcel (auto-generates ANX- tracking number):
    /addparcel John_Doe Business_Documents

  Update parcel status (auto-notifies customer on Telegram):
    /updateparcel ANX-XXXXXXXXXX Out_for_Delivery

  View all parcels:
    /listparcels

  Delete a parcel:
    /deleteparcel ANX-XXXXXXXXXX

  Common status options:
    Order_Received
    Collection_Scheduled
    Picked_Up
    Dispatched
    In_Transit
    Network_Dispatch
    Customs_Clearance
    Out_for_Delivery
    Delivered

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW TO USE — CUSTOMER TRACKING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  On the website:
    Customer enters their ANX- number in the tracking field.
    The site connects to server.py and shows live status.
    (Requires server.py to be running on the same machine)

  On Telegram:
    /track ANX-XXXXXXXXXX

  Once tracked via Telegram, the customer automatically
  receives a notification every time you update the status.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NOTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  - Data is saved in parcels.json (same folder)
  - Both bot.py and server.py must be running for
    website tracking to work
  - Use underscores instead of spaces in commands
  - Customers must use /track at least once on Telegram
    to receive push notifications
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

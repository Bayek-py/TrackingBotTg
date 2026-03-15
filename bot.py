import os
import json
import random
import string
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TimedOut, NetworkError
from keep_alive import keep_alive

logging.basicConfig(
    format="%(asctime)s — %(levelname)s — %(message)s",
    level=logging.WARNING
)

# ── CONFIG ───────────────────────────────────────────────────────────────────
TOKEN = os.environ.get("BOT_TOKEN", "8691586096:AAEJv26VPF_7N8n-hcGl1TTyP38GQ-ehvZY")
DATA_FILE   = os.path.join(os.path.dirname(__file__), "parcels.json")
ESCROW_FILE = os.path.join(os.path.dirname(__file__), "escrow.json")

# ── PAYMENT ADDRESSES ────────────────────────────────────────────────────────
BTC_ADDRESS = "bc1qra8rcqm6jcw4tntl3sgkzmvfuaw656f54jdm6z"
XMR_ADDRESS = "89wwRhbcyPhZeZV2RrNNZBhPjKGjXNFKY7eK2fX3EFTd3FXHs8in8JhTQhLhoYV4yBiWJSra9RJCt7xyKkfqWMgBGPVtSQz"

# ── DATA HELPERS ─────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"parcels": {}, "admin_ids": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_escrow():
    if os.path.exists(ESCROW_FILE):
        with open(ESCROW_FILE, "r") as f:
            return json.load(f)
    return {"escrows": {}}

def save_escrow(data):
    with open(ESCROW_FILE, "w") as f:
        json.dump(data, f, indent=2)

def gen_tracking_number():
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    return f"ANX-{suffix}"

# ── CUSTOMER COMMANDS ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📦 *Welcome to AnonXpress Tracking*\n"
        "_Private Courier — AU & USA Internal Shipping Network_\n\n"
        "*How to use escrow:*\n"
        "1️⃣ `/createescrow` — Get payment addresses & your escrow reference\n"
        "2️⃣ Send BTC or XMR to the address shown\n"
        "3️⃣ Message us on Signal `anonxpress.16` with your reference\n"
        "4️⃣ We confirm payment & ship your parcel\n\n"
        "*Other commands:*\n"
        "`/track <tracking_number>` — Track your shipment\n"
        "`/escrowstatus <reference>` — Check escrow status\n"
        "`/disputeescrow <reference>` — Raise a dispute\n\n"
        "Support: Signal `anonxpress.16` _(response within 1 hour)_",
        parse_mode="Markdown"
    )

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()

    if not context.args:
        await update.message.reply_text(
            "📦 Please provide your tracking number.\n"
            "Example: `/track PKG-ABC1234567`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    parcel = data["parcels"].get(tracking_num)

    if not parcel:
        await update.message.reply_text(
            f"❌ Tracking number `{tracking_num}` was not found.\n"
            "Please double-check your number and try again.\n\n"
            "_AnonXpress — Private International Courier_",
            parse_mode="Markdown"
        )
        return

    # Register customer's chat ID so admin updates can notify them
    parcel["chat_id"] = update.effective_chat.id
    save_data(data)

    history_lines = "\n".join(
        [f"  `{h['date']}` — {h['status']}" for h in parcel.get("history", [])]
    )

    msg = (
        f"📦 *AnonXpress Shipment Tracking*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 Tracking No: `{tracking_num}`\n"
        f"👤 Customer: {parcel['customer_name']}\n"
        f"🛍️ Item: {parcel['description']}\n"
        f"📍 Current Status: *{parcel['status']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Shipment History:*\n{history_lines}\n\n"
        f"_AnonXpress — Confidential. Discreet. Delivered._"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# ── ADMIN COMMANDS ────────────────────────────────────────────────────────────

async def setup_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """First-time admin registration. Run /setupadmin to register yourself."""
    data = load_data()
    user_id = update.effective_user.id

    if user_id not in data.get("admin_ids", []):
        data.setdefault("admin_ids", []).append(user_id)
        save_data(data)
        await update.message.reply_text(
            f"✅ *Admin registered successfully!*\n"
            f"Your Telegram ID: `{user_id}`",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"You are already an admin.\nYour ID: `{user_id}`",
            parse_mode="Markdown"
        )

async def add_parcel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Add a new parcel and generate a tracking number.
    Usage: /addparcel <customer_name> <item_description>
    Example: /addparcel John_Doe Nike_Shoes_Size10
    """
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/addparcel <customer_name> <item_description>`\n"
            "Example: `/addparcel John_Doe Nike_Shoes_Size10`\n\n"
            "_(Use underscores for spaces)_",
            parse_mode="Markdown"
        )
        return

    customer_name = context.args[0].replace("_", " ")
    description = " ".join(context.args[1:]).replace("_", " ")
    tracking_num = gen_tracking_number()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    data["parcels"][tracking_num] = {
        "customer_name": customer_name,
        "description": description,
        "status": "Order Received",
        "chat_id": None,
        "created": now,
        "history": [{"date": now, "status": "Order Received"}]
    }
    save_data(data)

    await update.message.reply_text(
        f"✅ *AnonXpress — Parcel Registered*\n\n"
        f"👤 Customer: {customer_name}\n"
        f"🛍️ Item: {description}\n"
        f"🔢 Tracking Number: `{tracking_num}`\n\n"
        f"📤 Share this tracking number with the customer.\n"
        f"They can track it using `/track {tracking_num}`\n\n"
        f"💰 To set up escrow: `/createescrow {tracking_num} <btc_amount>`",
        parse_mode="Markdown"
    )

async def update_parcel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Update parcel status and notify the customer automatically.
    Usage: /updateparcel <tracking_number> <new_status>
    Example: /updateparcel PKG-ABC1234567 Out_for_Delivery
    """
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/updateparcel <tracking_number> <new_status>`\n"
            "Example: `/updateparcel PKG-ABC1234567 Out_for_Delivery`\n\n"
            "Common statuses:\n"
            "• `Order_Received`\n"
            "• `Processing`\n"
            "• `Dispatched`\n"
            "• `In_Transit`\n"
            "• `Out_for_Delivery`\n"
            "• `Delivered`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    new_status = " ".join(context.args[1:]).replace("_", " ")
    parcel = data["parcels"].get(tracking_num)

    if not parcel:
        await update.message.reply_text(
            f"❌ Tracking number `{tracking_num}` not found.",
            parse_mode="Markdown"
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parcel["status"] = new_status
    parcel["history"].append({"date": now, "status": new_status})
    save_data(data)

    await update.message.reply_text(
        f"✅ *AnonXpress — Status Updated*\n"
        f"🔢 `{tracking_num}`\n"
        f"📍 New Status: *{new_status}*",
        parse_mode="Markdown"
    )

    # Auto-notify customer if they have registered via /track
    if parcel.get("chat_id"):
        try:
            await context.bot.send_message(
                chat_id=parcel["chat_id"],
                text=(
                    f"📦 *AnonXpress Shipment Update*\n\n"
                    f"🔢 Tracking: `{tracking_num}`\n"
                    f"🛍️ Item: {parcel['description']}\n"
                    f"📍 New Status: *{new_status}*\n\n"
                    f"Use `/track {tracking_num}` for full history.\n\n"
                    f"_AnonXpress — Confidential. Discreet. Delivered._"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass  # Customer may not have started the bot yet

async def list_parcels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all parcels with their current status."""
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    parcels = data["parcels"]
    if not parcels:
        await update.message.reply_text("📭 No parcels found.")
        return

    lines = ["📋 *All Parcels:*\n"]
    for num, p in parcels.items():
        notified = "🔔" if p.get("chat_id") else "🔕"
        lines.append(
            f"{notified} `{num}`\n"
            f"  👤 {p['customer_name']} — {p['description']}\n"
            f"  📍 *{p['status']}*\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def delete_parcel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a parcel record. Usage: /deleteparcel <tracking_number>"""
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/deleteparcel <tracking_number>`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    if tracking_num in data["parcels"]:
        del data["parcels"][tracking_num]
        save_data(data)
        await update.message.reply_text(f"🗑️ Parcel `{tracking_num}` deleted.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ `{tracking_num}` not found.", parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    is_admin = update.effective_user.id in data.get("admin_ids", [])

    msg = "📦 *AnonXpress Tracking Bot — Commands*\n_Private International Courier_\n\n"
    msg += "*For Customers:*\n"
    msg += "`/createescrow` — Create escrow & get payment addresses\n"
    msg += "`/track <tracking_number>` — Track your parcel\n"
    msg += "`/escrowstatus <reference>` — Check escrow status\n"
    msg += "`/disputeescrow <reference>` — Raise an escrow dispute\n"
    msg += "`/help` — Show this help menu\n"

    if is_admin:
        msg += "\n*For Admins:*\n"
        msg += "`/bookescrow <name> <item> <amount> [BTC|XMR]` — Book shipment with escrow\n"
        msg += "`/confirmpayment <number>` — Confirm payment received\n"
        msg += "`/updateparcel <number> <status>` — Update shipment status\n"
        msg += "`/releaseescrow <number>` — Release escrow after delivery\n"
        msg += "`/listparcels` — View all parcels\n"
        msg += "`/listescrows` — View all escrows\n"
        msg += "`/deleteparcel <number>` — Delete a parcel\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# ── ESCROW COMMANDS ───────────────────────────────────────────────────────────

ESCROW_STATUS_LABELS = {
    "awaiting_payment": "⏳ Awaiting Payment",
    "payment_received": "🔒 Payment Held in Escrow",
    "released":         "✅ Funds Released",
    "disputed":         "⚠️ Under Dispute",
}

async def book_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin: create a parcel + escrow in one step. Tracking number is issued WITH payment details.
    Usage: /bookescrow <customer_name> <item_description> <amount> [BTC|XMR]
    Example: /bookescrow John_Doe Business_Documents 0.005 BTC
    Example: /bookescrow Jane_Smith Legal_Papers 1.5 XMR
    """
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: `/bookescrow <customer_name> <item> <amount> [BTC|XMR]`\n"
            "Example: `/bookescrow John_Doe Documents 0.005 BTC`\n"
            "Example: `/bookescrow Jane_Smith Parcel 1.5 XMR`\n\n"
            "_(Currency defaults to BTC if not specified)_",
            parse_mode="Markdown"
        )
        return

    customer_name = context.args[0].replace("_", " ")
    description   = context.args[1].replace("_", " ")
    amount        = context.args[2]
    currency      = context.args[3].upper() if len(context.args) >= 4 else "BTC"

    if currency not in ("BTC", "XMR"):
        await update.message.reply_text("❌ Currency must be `BTC` or `XMR`.", parse_mode="Markdown")
        return

    tracking_num = gen_tracking_number()
    now          = datetime.now().strftime("%Y-%m-%d %H:%M")
    address      = BTC_ADDRESS if currency == "BTC" else XMR_ADDRESS
    symbol       = "₿" if currency == "BTC" else "ɱ"

    # Create parcel record (pending payment)
    data["parcels"][tracking_num] = {
        "customer_name": customer_name,
        "description":   description,
        "status":        "Awaiting Payment",
        "chat_id":       None,
        "created":       now,
        "history":       [{"date": now, "status": "Awaiting Payment"}]
    }
    save_data(data)

    # Create escrow record
    escrow_data = load_escrow()
    escrow_data["escrows"][tracking_num] = {
        "amount":   amount,
        "currency": currency,
        "address":  address,
        "status":   "awaiting_payment",
        "created":  now,
        "history":  [{"date": now, "event": f"Escrow created — awaiting {currency} payment"}]
    }
    save_escrow(escrow_data)

    # Reply to admin
    await update.message.reply_text(
        f"🔐 *AnonXpress — Booking Created*\n\n"
        f"🔢 Tracking: `{tracking_num}`\n"
        f"👤 Customer: {customer_name}\n"
        f"🛍️ Item: {description}\n"
        f"{symbol} Amount: `{amount} {currency}`\n"
        f"📬 {currency} Address:\n`{address}`\n\n"
        f"Send the customer their tracking number and payment details.\n"
        f"Run `/confirmpayment {tracking_num}` once payment is received.",
        parse_mode="Markdown"
    )

async def create_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Customer: create an escrow request.
    Usage: /createescrow [btc|xmr]
    Example: /createescrow btc
    Example: /createescrow xmr
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    ref = "ESC-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    chat_id = update.effective_chat.id

    escrow_data = load_escrow()
    escrow_data["escrows"][ref] = {
        "status":   "awaiting_payment",
        "created":  now,
        "chat_id":  chat_id,
        "history":  [{"date": now, "event": "Escrow created by customer"}]
    }
    save_escrow(escrow_data)

    await update.message.reply_text(
        f"🔐 *Escrow Created — AnonXpress*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Reference: `{ref}`\n\n"
        f"Pay whenever you're ready using either address below:\n\n"
        f"*Bitcoin (BTC):*\n`{BTC_ADDRESS}`\n\n"
        f"*Monero (XMR):*\n`{XMR_ADDRESS}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Once payment is sent, share your reference `{ref}` with our team on Signal: `anonxpress.16`\n\n"
        f"Use `/escrowstatus {ref}` to check your escrow status.\n\n"
        f"_AnonXpress — Confidential. Discreet. Delivered._",
        parse_mode="Markdown"
    )

async def confirm_escrow_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: mark BTC payment as received. Usage: /confirmpayment <tracking_number>"""
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/confirmpayment <reference> <amount> [BTC|XMR]`\n"
            "Example: `/confirmpayment ESC-NRJR98JD 0.005 BTC`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    escrow_data = load_escrow()
    escrow = escrow_data["escrows"].get(tracking_num)

    if not escrow:
        await update.message.reply_text(
            f"❌ No escrow found for `{tracking_num}`.",
            parse_mode="Markdown"
        )
        return

    # Update amount/currency if provided
    if len(context.args) >= 2:
        escrow["amount"] = context.args[1]
    if len(context.args) >= 3:
        escrow["currency"] = context.args[2].upper()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    escrow["status"] = "payment_received"
    escrow["history"].append({"date": now, "event": "Payment confirmed — funds held in escrow"})
    save_escrow(escrow_data)

    # Activate parcel: update status from "Awaiting Payment" to "Order Received"
    parcel = data["parcels"].get(tracking_num)
    if parcel and parcel.get("status") == "Awaiting Payment":
        parcel["status"] = "Order Received"
        parcel["history"].append({"date": now, "status": "Order Received"})
        save_data(data)

    cur = escrow.get("currency", "")
    amt = escrow.get("amount", escrow.get("btc_amount", ""))
    amt_str = f"`{amt} {cur}`" if amt else "funds"

    await update.message.reply_text(
        f"✅ *Escrow Payment Confirmed*\n"
        f"🔢 `{tracking_num}`\n"
        f"{amt_str} held in escrow.\n"
        f"Use `/addparcel <name> <item>` to create their tracking number.",
        parse_mode="Markdown"
    )

    # Notify customer — check parcel first, fall back to escrow's chat_id
    customer_chat = (parcel.get("chat_id") if parcel else None) or escrow.get("chat_id")
    if customer_chat:
        try:
            await context.bot.send_message(
                chat_id=customer_chat,
                text=(
                    f"🔒 *AnonXpress — Payment Confirmed*\n\n"
                    f"📋 Reference: `{tracking_num}`\n"
                    f"Payment received and held securely in escrow.\n\n"
                    f"Your shipment is now being processed. You will receive a tracking number shortly.\n"
                    f"Funds will be released upon confirmed delivery.\n\n"
                    f"_AnonXpress — Confidential. Discreet. Delivered._"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def release_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: release escrow after delivery. Usage: /releaseescrow <tracking_number>"""
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: `/releaseescrow <tracking_number>`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    escrow_data = load_escrow()
    escrow = escrow_data["escrows"].get(tracking_num)

    if not escrow:
        await update.message.reply_text(
            f"❌ No escrow found for `{tracking_num}`.",
            parse_mode="Markdown"
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    escrow["status"] = "released"
    escrow["released"] = now
    escrow["history"].append({"date": now, "event": "Delivery confirmed — funds released"})
    save_escrow(escrow_data)

    cur = escrow.get("currency", "BTC")
    amt = escrow.get("amount", escrow.get("btc_amount", "?"))

    await update.message.reply_text(
        f"✅ *Escrow Released*\n"
        f"🔢 `{tracking_num}`\n"
        f"`{amt} {cur}` — funds released.",
        parse_mode="Markdown"
    )

    # Notify customer
    parcel = data["parcels"].get(tracking_num)
    if parcel and parcel.get("chat_id"):
        try:
            await context.bot.send_message(
                chat_id=parcel["chat_id"],
                text=(
                    f"✅ *AnonXpress — Delivery Confirmed & Escrow Released*\n\n"
                    f"🔢 Tracking: `{tracking_num}`\n"
                    f"Escrow of `{amt} {cur}` has been released.\n\n"
                    f"Thank you for shipping with AnonXpress.\n\n"
                    f"_AnonXpress — Confidential. Discreet. Delivered._"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def dispute_escrow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anyone: raise a dispute. Usage: /disputeescrow <tracking_number>"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/disputeescrow <tracking_number>`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    escrow_data = load_escrow()
    escrow = escrow_data["escrows"].get(tracking_num)

    if not escrow:
        await update.message.reply_text(
            f"❌ No escrow found for `{tracking_num}`.\n"
            "Contact @AnonXpressTrackingbot directly.",
            parse_mode="Markdown"
        )
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    escrow["status"] = "disputed"
    escrow["history"].append({
        "date": now,
        "event": f"Dispute raised by user {update.effective_user.id}"
    })
    save_escrow(escrow_data)

    await update.message.reply_text(
        f"⚠️ *Escrow Dispute Raised*\n"
        f"🔢 `{tracking_num}`\n\n"
        f"Our team has been notified and will review within 24 hours.\n"
        f"Contact us directly: @AnonXpressTrackingbot\n\n"
        f"_AnonXpress — Confidential. Discreet. Delivered._",
        parse_mode="Markdown"
    )

    # Alert all admins
    admin_data = load_data()
    cur = escrow.get("currency", "BTC")
    amt = escrow.get("amount", escrow.get("btc_amount", "?"))
    for admin_id in admin_data.get("admin_ids", []):
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🚨 *ESCROW DISPUTE RAISED*\n\n"
                    f"🔢 Tracking: `{tracking_num}`\n"
                    f"👤 User ID: `{update.effective_user.id}`\n"
                    f"Amount: `{amt} {cur}`\n\n"
                    f"Immediate review required."
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def escrow_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anyone: check escrow status. Usage: /escrowstatus <tracking_number>"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/escrowstatus <tracking_number>`",
            parse_mode="Markdown"
        )
        return

    tracking_num = context.args[0].upper()
    escrow_data = load_escrow()
    escrow = escrow_data["escrows"].get(tracking_num)

    if not escrow:
        await update.message.reply_text(
            f"❌ No escrow found for `{tracking_num}`.\n\n"
            "To set up escrow for your shipment, contact us on Telegram: @AnonXpressTrackingbot",
            parse_mode="Markdown"
        )
        return

    status_label = ESCROW_STATUS_LABELS.get(escrow["status"], escrow["status"])
    cur = escrow.get("currency", "BTC")
    amt = escrow.get("amount", escrow.get("btc_amount", "?"))
    history_lines = "\n".join(
        [f"  `{h['date']}` — {h['event']}" for h in escrow.get("history", [])]
    )

    msg = (
        f"🔐 *AnonXpress Escrow Status*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 Tracking: `{tracking_num}`\n"
        f"Amount: `{amt} {cur}`\n"
        f"📍 Status: *{status_label}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Escrow History:*\n{history_lines}\n\n"
        f"_AnonXpress — Confidential. Discreet. Delivered._"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def list_escrows(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: list all escrows. Usage: /listescrows"""
    data = load_data()
    if update.effective_user.id not in data.get("admin_ids", []):
        await update.message.reply_text("⛔ This command is for admins only.")
        return

    escrow_data = load_escrow()
    escrows = escrow_data["escrows"]

    if not escrows:
        await update.message.reply_text("📭 No escrows found.")
        return

    status_icons = {
        "awaiting_payment": "⏳",
        "payment_received": "🔒",
        "released":         "✅",
        "disputed":         "⚠️",
    }

    lines = ["💰 *All Escrows:*\n"]
    for num, e in escrows.items():
        icon = status_icons.get(e["status"], "❓")
        cur = e.get("currency", "BTC")
        amt = e.get("amount", e.get("btc_amount", "?"))
        lines.append(
            f"{icon} `{num}`\n"
            f"  {amt} {cur} — *{e['status'].replace('_', ' ').title()}*\n"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

# ── ERROR HANDLER ─────────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, (TimedOut, NetworkError)):
        return  # silently ignore — polling will auto-retry
    logging.warning(f"Update {update} caused error: {context.error}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .pool_timeout(30)
        .build()
    )

    # Parcel commands
    app.add_handler(CommandHandler("start",         start))
    app.add_handler(CommandHandler("track",         track))
    app.add_handler(CommandHandler("help",          help_cmd))
    app.add_handler(CommandHandler("setupadmin",    setup_admin))
    app.add_handler(CommandHandler("addparcel",     add_parcel))
    app.add_handler(CommandHandler("updateparcel",  update_parcel))
    app.add_handler(CommandHandler("listparcels",   list_parcels))
    app.add_handler(CommandHandler("deleteparcel",  delete_parcel))

    # Escrow commands
    app.add_handler(CommandHandler("bookescrow",      book_escrow))
    app.add_handler(CommandHandler("createescrow",    create_escrow))
    app.add_handler(CommandHandler("confirmpayment",  confirm_escrow_payment))
    app.add_handler(CommandHandler("releaseescrow",   release_escrow))
    app.add_handler(CommandHandler("disputeescrow",   dispute_escrow))
    app.add_handler(CommandHandler("escrowstatus",    escrow_status))
    app.add_handler(CommandHandler("listescrows",     list_escrows))

    app.add_error_handler(error_handler)

    keep_alive()
    print("🤖 AnonXpress Tracking Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()


import os
import re
import socket
import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

import database as db


TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

db.init_db()
db.add_admin(ADMIN_ID)


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🐙 GitHub Lookup",
                callback_data="github_help"
            )
        ],
        [
            InlineKeyboardButton(
                "🌐 Domain Lookup",
                callback_data="domain_help"
            )
        ],
        [
            InlineKeyboardButton(
                "🆔 My Account",
                callback_data="account"
            )
        ],
        [
            InlineKeyboardButton(
                "📚 Help",
                callback_data="help"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    db.register_user(
        user.id,
        user.username,
        user.first_name
    )

    if db.is_blocked(user.id):
        await update.message.reply_text(
            "⛔ Your account is blocked."
        )
        return

    if db.get_setting("maintenance_mode", "0") == "1":
        if not db.is_admin(user.id):
            await update.message.reply_text(
                "🔧 Bot is under maintenance. Please try later."
            )
            return

    await update.message.reply_text(
        "🔥 FREE ARPIT OSINT BOT\n\n"
        f"Welcome, {user.first_name}!\n\n"
        "Select a feature from the menu below.",
        reply_markup=main_menu()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 AVAILABLE COMMANDS\n\n"
        "/start - Main menu\n"
        "/help - Help\n"
        "/id - Your Telegram ID\n"
        "/github username - Public GitHub profile\n"
        "/domain example.com - DNS lookup\n"
        "/credits - Check your credits\n\n"
        "ADMIN COMMANDS\n"
        "/stats - Bot statistics\n"
        "/addcredits USER_ID AMOUNT\n"
        "/block USER_ID\n"
        "/unblock USER_ID\n"
        "/maintenance on/off"
    )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 Your Telegram ID: {update.effective_user.id}"
    )


async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.get_user(user_id)

    if not user:
        db.register_user(user_id)
        user = db.get_user(user_id)

    await update.message.reply_text(
        f"💳 Your credits: {user['credits']}"
    )


async def account_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = db.get_user(query.from_user.id)

    if not user:
        db.register_user(query.from_user.id)
        user = db.get_user(query.from_user.id)

    await query.message.reply_text(
        "👤 MY ACCOUNT\n\n"
        f"User ID: {user['user_id']}\n"
        f"Credits: {user['credits']}\n"
        f"Status: {'Blocked' if user['is_blocked'] else 'Active'}"
    )


async def github_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if db.is_blocked(user_id):
        await update.message.reply_text("⛔ Account blocked.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /github username"
        )
        return

    username = context.args[0].strip()

    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", username):
        await update.message.reply_text("❌ Invalid GitHub username.")
        return

    user = db.get_user(user_id)

    if not user:
        db.register_user(user_id)
        user = db.get_user(user_id)

    if user["credits"] < 1:
        await update.message.reply_text("❌ Not enough credits.")
        return

    await update.message.reply_text("🔎 Searching public GitHub profile...")

    try:
        response = requests.get(
            f"https://api.github.com/users/{username}",
            timeout=10,
            headers={"Accept": "application/vnd.github+json"}
        )

        if response.status_code == 404:
            await update.message.reply_text("❌ User not found.")
            return

        response.raise_for_status()
        data = response.json()

        if not db.deduct_credit(user_id):
            await update.message.reply_text("❌ Not enough credits.")
            return

        db.log_search(user_id, "github", username)

        await update.message.reply_text(
            "🐙 GITHUB PROFILE\n\n"
            f"👤 Name: {data.get('name') or 'N/A'}\n"
            f"🔗 Username: {data['login']}\n"
            f"📦 Public repos: {data['public_repos']}\n"
            f"👥 Followers: {data['followers']}\n"
            f"➡️ Following: {data['following']}\n"
            f"🌍 Location: {data.get('location') or 'N/A'}\n"
            f"🔗 Profile: {data['html_url']}\n\n"
            "💳 1 credit used."
        )

    except requests.RequestException:
        await update.message.reply_text(
            "⚠️ GitHub lookup failed. Please try again."
        )


async def domain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if db.is_blocked(user_id):
        await update.message.reply_text("⛔ Account blocked.")
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /domain example.com"
        )
        return

    domain = context.args[0].strip().lower()

    if (
        len(domain) > 253
        or not re.fullmatch(
            r"(?=.{1,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}",
            domain
        )
    ):
        await update.message.reply_text("❌ Invalid domain.")
        return

    user = db.get_user(user_id)

    if not user:
        db.register_user(user_id)
        user = db.get_user(user_id)

    if user["credits"] < 1:
        await update.message.reply_text("❌ Not enough credits.")
        return

    try:
        ip = socket.gethostbyname(domain)

        if not db.deduct_credit(user_id):
            await update.message.reply_text("❌ Not enough credits.")
            return

        db.log_search(user_id, "domain", domain)

        await update.message.reply_text(
            "🌐 DOMAIN INFORMATION\n\n"
            f"Domain: {domain}\n"
            f"Resolved IP: {ip}\n\n"
            "💳 1 credit used."
        )

    except socket.gaierror:
        await update.message.reply_text(
            "❌ Domain could not be resolved."
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "github_help":
        await query.message.reply_text(
            "🐙 GitHub Lookup\n\n"
            "Use: /github username"
        )

    elif query.data == "domain_help":
        await query.message.reply_text(
            "🌐 Domain Lookup\n\n"
            "Use: /domain example.com"
        )

    elif query.data == "account":
        await account_callback(update, context)

    elif query.data == "help":
        await query.message.reply_text(
            "Use /help to see all available commands."
        )


def admin_only(user_id):
    return db.is_admin(user_id)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    stats = db.get_stats()

    await update.message.reply_text(
        "📊 BOT STATISTICS\n\n"
        f"👥 Total users: {stats['total_users']}\n"
        f"🚫 Blocked users: {stats['blocked_users']}\n"
        f"🔎 Total searches: {stats['total_searches']}\n"
        f"💳 Total credits: {stats['total_credits']}"
    )


async def addcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /addcredits USER_ID AMOUNT"
        )
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])

        if amount <= 0 or amount > 100000:
            raise ValueError

        if not db.get_user(user_id):
            await update.message.reply_text("❌ User not found.")
            return

        db.add_credits(user_id, amount)

        await update.message.reply_text(
            f"✅ Added {amount} credits to {user_id}."
        )

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or amount.")


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /block USER_ID")
        return

    try:
        user_id = int(context.args[0])

        if user_id == ADMIN_ID:
            await update.message.reply_text("❌ Cannot block primary admin.")
            return

        db.set_blocked(user_id, True)
        await update.message.reply_text(f"🚫 User {user_id} blocked.")

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")


async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /unblock USER_ID")
        return

    try:
        user_id = int(context.args[0])
        db.set_blocked(user_id, False)
        await update.message.reply_text(f"✅ User {user_id} unblocked.")

    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")


async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin_only(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text(
            "Usage: /maintenance on/off"
        )
        return

    value = "1" if context.args[0].lower() == "on" else "0"
    db.set_setting("maintenance_mode", value)

    await update.message.reply_text(
        f"🔧 Maintenance mode: {context.args[0].upper()}"
    )


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("credits", credits_command))
    app.add_handler(CommandHandler("github", github_command))
    app.add_handler(CommandHandler("domain", domain_command))

    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("addcredits", addcredits_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CommandHandler("maintenance", maintenance_command))

    app.add_handler(CallbackQueryHandler(callback_handler))

    print("FREE ARPIT OSINT BOT is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

"""
Data Analyst Telegram Bot powered by Google Gemini AI
======================================================
Send a CSV/Excel file, then ask questions about your data in plain English.
"""

import os
import logging
import traceback
import pandas as pd
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from agent import run_agent

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = ""

# Per-user state: { chat_id: { "filepath": str, "filename": str, "history": list } }
user_state: dict = {}


# ── Helpers ──────────────────────────────────────────────────────────────────
def get_state(chat_id: int) -> dict:
    if chat_id not in user_state:
        user_state[chat_id] = {"filepath": None, "filename": None, "history": []}
    return user_state[chat_id]


# ── Handlers ──────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to the Data Analyst Bot!*\n\n"
        "Powered by Google Gemini AI 🤖\n\n"
        "Here's how to use me:\n"
        "1️⃣ Upload a *CSV or Excel* file\n"
        "2️⃣ Ask me anything about your data in plain English\n\n"
        "Examples:\n"
        "• _What are the top 5 products by revenue?_\n"
        "• _Show me monthly sales as a bar chart_\n"
        "• _Are there any missing values?_\n\n"
        "Type /help for more commands.",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Commands*\n"
        "/start – Welcome message\n"
        "/help  – Show this help\n"
        "/clear – Clear loaded data & chat history\n\n"
        "*Tips*\n"
        "• Upload a new file any time to replace the current one\n"
        "• Ask follow-up questions – the bot remembers context\n"
        "• Request charts: _'plot revenue over time as a bar chart'_",
        parse_mode="Markdown",
    )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_state[chat_id] = {"filepath": None, "filename": None, "history": []}
    await update.message.reply_text(
        "🗑️ Data and history cleared. Upload a new file to start fresh."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Accept CSV or Excel uploads."""
    chat_id = update.effective_chat.id
    doc = update.message.document
    fname = doc.file_name or "upload"

    if not (fname.endswith(".csv") or fname.endswith(".xlsx") or fname.endswith(".xls")):
        await update.message.reply_text(
            "⚠️ Please upload a *CSV* or *Excel* (.xlsx/.xls) file.",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("📥 Downloading your file…")
    tg_file = await context.bot.get_file(doc.file_id)
    import os
    os.makedirs("downloads", exist_ok=True)
    save_path = os.path.join("downloads", f"{chat_id}_{fname}")

    await tg_file.download_to_drive(save_path)

    # Quick validation
    try:
        df = pd.read_csv(save_path, nrows=5) if fname.endswith(".csv") else pd.read_excel(save_path, nrows=5)
    except Exception as e:
        await update.message.reply_text(f"❌ Could not read file: {e}")
        return

    state = get_state(chat_id)
    state["filepath"] = save_path
    state["filename"] = fname
    state["history"] = []  # reset conversation for new file

    await update.message.reply_text(
        f"✅ *{fname}* loaded!\n"
        f"Columns: `{', '.join(df.columns.tolist())}`\n\n"
        "Now ask me anything about your data 🚀",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text messages to the Gemini agent."""
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()
    state = get_state(chat_id)

    if not state["filepath"]:
        await update.message.reply_text(
            "📂 Please upload a CSV or Excel file first, then ask your question."
        )
        return

    thinking_msg = await update.message.reply_text("🤔 Analyzing…")

    try:
        answer, chart_path = await run_agent(
            user_message=user_text,
            filepath=state["filepath"],
            history=state["history"],
        )

        # Update history
        state["history"].append({"role": "user", "parts": [user_text]})
        state["history"].append({"role": "model", "parts": [answer]})

        await context.bot.delete_message(chat_id=chat_id, message_id=thinking_msg.message_id)
        await update.message.reply_text(answer, parse_mode="Markdown")

        if chart_path and os.path.exists(chart_path):
            with open(chart_path, "rb") as img:
                await update.message.reply_photo(photo=img)
            os.remove(chart_path)

    except Exception:
        logger.error(traceback.format_exc())
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=thinking_msg.message_id,
            text="❌ Something went wrong. Please try again.",
        )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running… Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()

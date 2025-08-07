import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))

vaults = [
    {
        "name": "SUI-USDC",
        "category": "Momentum Vaults",
        "url": "https://ai.nodo.xyz/vault/0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb"
    },
    {
        "name": "DEEP-SUI",
        "category": "Momentum Vaults",
        "url": "https://ai.nodo.xyz/vault/0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448"
    },
    {
        "name": "WAL-SUI",
        "category": "Momentum Vaults",
        "url": "https://ai.nodo.xyz/vault/0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0"
    },
    {
        "name": "SUI-USDC",
        "category": "Cetus Vault",
        "url": "https://ai.nodo.xyz/vault/0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989"
    }
]

async def check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🔍 Checking vaults...\n\n"
    for v in vaults:
        text += f"**{v['category']}**\n[{v['name']}]({v['url']})\n\n"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Bot is online and working."
    )

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("check", check_handler))
    app.add_handler(CommandHandler("status", status_handler))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

import os
import logging
import asyncio
import httpx
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Apply patch for asyncio event loop reuse
nest_asyncio.apply()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1002653992951  # Make sure this is correct and your bot is admin here

# Vaults to monitor
VAULTS = [
    {
        "platform": "Momentum Vaults",
        "name": "SUI-USDC",
        "address": "0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb",
        "link": "https://ai.nodo.xyz/vault/0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb",
        "last_tvl": None,
    },
    {
        "platform": "Momentum Vaults",
        "name": "DEEP-SUI",
        "address": "0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448",
        "link": "https://ai.nodo.xyz/vault/0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448",
        "last_tvl": None,
    },
    {
        "platform": "Momentum Vaults",
        "name": "WAL-SUI",
        "address": "0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0",
        "link": "https://ai.nodo.xyz/vault/0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0",
        "last_tvl": None,
    },
    {
        "platform": "Cetus Vault",
        "name": "SUI-USDC",
        "address": "0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989",
        "link": "https://ai.nodo.xyz/vault/0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989",
        "last_tvl": None,
    },
]

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is live and ready.")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is live and monitoring vaults.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Status OK. Vault tracking is active.")

async def apy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt")
        data = response.json()

    messages = []
    for vault in VAULTS:
        item = next((v for v in data if v["address"] == vault["address"]), None)
        if not item:
            continue
        apy = round(item.get("apy", 0), 2)
        tvl = round(item.get("tvl", 0))
        messages.append(
            f"{vault['platform']}: [{vault['name']}]\n\n"
            f"📈 APY: {apy}%\n"
            f"💰 TVL: ${tvl:,.2f}\n"
            f"🔗 Open Vault: {vault['link']}"
        )

    await update.message.reply_text("\n\n".join(messages), disable_web_page_preview=False)

# Monitor function
async def monitor_vaults(app):
    async with httpx.AsyncClient() as client:
        response = await client.get("https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt")
        data = response.json()

    for vault in VAULTS:
        item = next((v for v in data if v["address"] == vault["address"]), None)
        if not item:
            continue

        current_tvl = item.get("tvl", 0)
        if vault["last_tvl"] is not None:
            diff = current_tvl - vault["last_tvl"]
            if diff > 100:
                message = (
                    f"🚨 New Deposit Alert!\n"
                    f"{vault['platform']}: {vault['name']}\n"
                    f"💸 Amount: ${diff:,.2f}\n"
                    f"📊 New TVL: ${current_tvl:,.2f}\n"
                    f"🔗 {vault['link']}"
                )
                await app.bot.send_message(chat_id=GROUP_ID, text=message, disable_web_page_preview=False)

        vault["last_tvl"] = current_tvl

# Scheduler
async def scheduler(app):
    while True:
        try:
            await monitor_vaults(app)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
        await asyncio.sleep(300)  # 5 mins

# Main app
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("apy", apy_command))

    asyncio.create_task(scheduler(app))
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())

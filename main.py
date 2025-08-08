import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram config
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "-1002653992951"))

# Vault config
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

API_URL = "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt"

async def check_deposits(context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.get(API_URL)
        data = res.json()["data"]

        for vault in VAULTS:
            vault_data = next((item for item in data if item["address"].lower() == vault["address"].lower()), None)
            if not vault_data:
                continue

            tvl = float(vault_data["tvl"]["value"])
            if vault["last_tvl"] is None:
                vault["last_tvl"] = tvl
                continue

            diff = round(tvl - vault["last_tvl"], 2)
            if diff >= 10:
                message = (
                    f"🚨 *New Deposit Alert!*\n"
                    f"{vault['platform']} - *{vault['name']}*\n"
                    f"💸 Amount: ${diff:,.2f}\n"
                    f"📊 New TVL: ${tvl:,.2f}\n"
                    f"🔗 [Open Vault]({vault['link']})"
                )
                await context.bot.send_message(chat_id=GROUP_ID, text=message, parse_mode="Markdown", disable_web_page_preview=False)

            vault["last_tvl"] = tvl

    except Exception as e:
        logger.error(f"Error checking vaults: {e}")

async def apy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        res = requests.get(API_URL)
        data = res.json()["data"]

        message = "*NODO Vault APY Stats*\n\n"
        for vault in VAULTS:
            vault_data = next((item for item in data if item["address"].lower() == vault["address"].lower()), None)
            if vault_data:
                apy = vault_data["apy"]
                tvl = vault_data["tvl"]["value"]
                message += (
                    f"{vault['platform']} - *{vault['name']}*\n"
                    f"📈 APY: {apy:.2f}%\n"
                    f"💰 TVL: ${tvl:,.2f}\n"
                    f"{vault['link']}\n\n"
                )

        await update.message.reply_text(message, parse_mode="Markdown", disable_web_page_preview=False)

    except Exception as e:
        logger.error(f"Error in /apy: {e}")
        await update.message.reply_text("Failed to fetch vault data.")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is live and monitoring vaults.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    statuses = [f"{v['platform']} - {v['name']}: ${v['last_tvl']:,.2f}" if v['last_tvl'] else f"{v['platform']} - {v['name']}: Not checked yet" for v in VAULTS]
    await update.message.reply_text("\n".join(statuses))

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("apy", apy_command))

    job_queue = app.job_queue
    job_queue.run_repeating(check_deposits, interval=60, first=5)

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

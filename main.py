import os
import asyncio
from fastapi import FastAPI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import httpx

# ENV
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MIN_TVL = float(os.getenv("MIN_TVL", "10"))

app = FastAPI()

vaults = [
    {
        "name": "SUI-USDC",
        "address": "0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb",
        "link": "https://ai.nodo.xyz/vault/0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb",
        "source": "Momentum Vaults"
    },
    {
        "name": "DEEP-SUI",
        "address": "0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448",
        "link": "https://ai.nodo.xyz/vault/0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448",
        "source": "Momentum Vaults"
    },
    {
        "name": "WAL-SUI",
        "address": "0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0",
        "link": "https://ai.nodo.xyz/vault/0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0",
        "source": "Momentum Vaults"
    },
    {
        "name": "SUI-USDC",
        "address": "0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989",
        "link": "https://ai.nodo.xyz/vault/0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989",
        "source": "Cetus Vault"
    },
]

# Telegram bot setup
tg_app = ApplicationBuilder().token(BOT_TOKEN).build()

# API endpoint for Galxe
@app.get("/api/depositors")
async def get_depositors():
    depositors = set()
    async with httpx.AsyncClient() as client:
        for vault in vaults:
            url = f"https://api.nodo.xyz/info/vault/{vault['address']}/deposits"
            try:
                response = await client.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                for entry in data:
                    amount = float(entry.get("usdValue", 0))
                    if amount >= MIN_TVL:
                        depositors.add(entry["address"].lower())
                        await send_alert(vault, entry["address"], amount)
            except Exception:
                continue
    return {"depositors": list(depositors)}

async def send_alert(vault, address, amount):
    msg = (
        f"🚨 New Deposit Alert!\n"
        f"{vault['source']} - {vault['name']}\n"
        f"💸 Wallet: `{address}`\n"
        f"💰 Amount: ${amount:.2f}\n"
        f"🔗 Vault: {vault['link']}"
    )
    await tg_app.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=False)

# Telegram Commands
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Checking vaults now...")
    await get_depositors()
    await update.message.reply_text("✅ Check complete.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is live and monitoring vaults.")

tg_app.add_handler(CommandHandler("check", check_command))
tg_app.add_handler(CommandHandler("status", status_command))

@app.on_event("startup")
async def startup():
    asyncio.create_task(tg_app.run_polling())

import os
import httpx
import asyncio
from fastapi import FastAPI, Request
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ENV
API_KEY = os.getenv("API_KEY")
NODO_API = os.getenv("NODO_API", "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt")
VAULT_ADDRESS = os.getenv("VAULT_ADDRESS")
MIN_TVL = float(os.getenv("MIN_TVL", "10"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# STATE
notified_wallets = set()
app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()

# 🚨 Send Telegram Alert
async def send_telegram_alert(wallet: str, tvl: float):
    message = (
        f"✅ New Eligible Wallet for Galxe\n\n"
        f"👛 Wallet: `{wallet}`\n"
        f"💰 TVL: ${tvl:,.2f}\n"
        f"🔗 Vault: https://ai.nodo.xyz/vault/{VAULT_ADDRESS}"
    )
    await tg_app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown", disable_web_page_preview=False)

# ✅ Telegram: /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online.")

# ✅ Telegram: /check <wallet>
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <wallet_address>")
        return

    wallet = context.args[0].lower()

    async with httpx.AsyncClient() as client:
        res = await client.get(NODO_API)
        data = res.json()

    for vault in data.get("data", []):
        if vault.get("address") == VAULT_ADDRESS:
            user_data = vault.get("wallets", {}).get(wallet)
            if user_data:
                tvl = float(user_data.get("tvl", 0))
                if tvl >= MIN_TVL and wallet not in notified_wallets:
                    await send_telegram_alert(wallet, tvl)
                    notified_wallets.add(wallet)
                status = "Eligible ✅" if tvl >= MIN_TVL else "Not Eligible ❌"
                await update.message.reply_text(f"👛 {wallet}\n📊 TVL: ${tvl:.2f}\nStatus: {status}")
                return

    await update.message.reply_text(f"👛 {wallet}\nStatus: No data ❌")

# ✅ FastAPI: /status
@app.get("/status")
async def status():
    return {"status": "online"}

# ✅ FastAPI: /check?wallet=0x...
@app.get("/check")
async def check(wallet: str):
    async with httpx.AsyncClient() as client:
        res = await client.get(NODO_API)
        data = res.json()

    for vault in data.get("data", []):
        if vault.get("address") == VAULT_ADDRESS:
            user_data = vault.get("wallets", {}).get(wallet.lower())
            if user_data:
                tvl = float(user_data.get("tvl", 0))
                if tvl >= MIN_TVL and wallet.lower() not in notified_wallets:
                    await send_telegram_alert(wallet, tvl)
                    notified_wallets.add(wallet.lower())
                status = "Eligible ✅" if tvl >= MIN_TVL else "Not Eligible ❌"
                return {
                    "wallet": wallet,
                    "status": status,
                    "tvl": tvl
                }

    return {
        "wallet": wallet,
        "status": "No data found ❌",
        "tvl": 0
    }

# ✅ Launch both FastAPI + Telegram
@app.on_event("startup")
async def startup():
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("check", check_command))
    asyncio.create_task(tg_app.run_polling())

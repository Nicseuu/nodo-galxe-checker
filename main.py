import os
import httpx
import asyncio
from fastapi import FastAPI, Request, Query, Header, HTTPException
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Env vars
API_KEY = os.getenv("API_KEY")
NODO_API = os.getenv("NODO_API", "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt")
MIN_TVL = float(os.getenv("MIN_TVL", "10"))
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Vaults to track
VAULTS = [
    {
        "name": "SUI-USDC",
        "group": "Momentum Vaults",
        "address": "0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb"
    },
    {
        "name": "DEEP-SUI",
        "group": "Momentum Vaults",
        "address": "0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448"
    },
    {
        "name": "WAL-SUI",
        "group": "Momentum Vaults",
        "address": "0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0"
    },
    {
        "name": "SUI-USDC",
        "group": "Cetus Vault",
        "address": "0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989"
    }
]

notified = {}
app = FastAPI()
tg_app = Application.builder().token(BOT_TOKEN).build()

async def send_telegram_alert(wallet: str, tvl: float, vault_name: str, group_name: str, vault_address: str):
    message = (
        f"✅ New Eligible Wallet for Galxe\n\n"
        f"🏦 Vault: *{group_name} - {vault_name}*\n"
        f"👛 Wallet: `{wallet}`\n"
        f"💰 TVL: ${tvl:,.2f}\n"
        f"https://ai.nodo.xyz/vault/{vault_address}"
    )
    await tg_app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown", disable_web_page_preview=False)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online.")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /check <wallet_address>")
        return
    wallet = context.args[0].lower()
    async with httpx.AsyncClient() as client:
        res = await client.get(NODO_API)
        data = res.json()

    results = []
    for vault in VAULTS:
        for item in data.get("data", []):
            if item.get("address") == vault["address"]:
                user_data = item.get("wallets", {}).get(wallet)
                if user_data:
                    tvl = float(user_data.get("tvl", 0))
                    status = "Eligible ✅" if tvl >= MIN_TVL else "Not Eligible ❌"
                    results.append(f"{vault['group']} - {vault['name']}:\nTVL: ${tvl:.2f} → {status}")
                    key = f"{wallet}:{vault['address']}"
                    if tvl >= MIN_TVL and key not in notified:
                        await send_telegram_alert(wallet, tvl, vault['name'], vault['group'], vault['address'])
                        notified[key] = True
                break

    if results:
        await update.message.reply_text("\n\n".join(results))
    else:
        await update.message.reply_text("No data found for wallet.")

@app.get("/status")
async def status():
    return {"status": "online"}

@app.get("/check")
async def check(wallet: str):
    wallet = wallet.lower()
    async with httpx.AsyncClient() as client:
        res = await client.get(NODO_API)
        data = res.json()

    output = []
    for vault in VAULTS:
        for item in data.get("data", []):
            if item.get("address") == vault["address"]:
                user_data = item.get("wallets", {}).get(wallet)
                if user_data:
                    tvl = float(user_data.get("tvl", 0))
                    key = f"{wallet}:{vault['address']}"
                    if tvl >= MIN_TVL and key not in notified:
                        await send_telegram_alert(wallet, tvl, vault['name'], vault['group'], vault['address'])
                        notified[key] = True
                    output.append({
                        "vault": f"{vault['group']} - {vault['name']}",
                        "wallet": wallet,
                        "tvl": tvl,
                        "status": "Eligible ✅" if tvl >= MIN_TVL else "Not Eligible ❌"
                    })
                break

    return output if output else {"wallet": wallet, "status": "No data found ❌", "tvl": 0}

@app.get("/api/depositors")
async def get_valid_wallets(wallets: list[str] = Query(...), authorization: str = Header(None)):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with httpx.AsyncClient() as client:
        res = await client.get(NODO_API)
        data = res.json()

    eligible = []
    for wallet in wallets:
        wallet = wallet.lower()
        for vault in VAULTS:
            for item in data.get("data", []):
                if item.get("address") == vault["address"]:
                    user_data = item.get("wallets", {}).get(wallet)
                    if user_data:
                        tvl = float(user_data.get("tvl", 0))
                        key = f"{wallet}:{vault['address']}"
                        if tvl >= MIN_TVL:
                            if key not in notified:
                                await send_telegram_alert(wallet, tvl, vault['name'], vault['group'], vault['address'])
                                notified[key] = True
                            eligible.append({
                                "id": wallet,
                                "timestamp": int(datetime.utcnow().timestamp())
                            })
                    break

    return {"credential": eligible}

@app.on_event("startup")
async def startup():
    tg_app.add_handler(CommandHandler("status", status_command))
    tg_app.add_handler(CommandHandler("check", check_command))
    await tg_app.initialize()
    await tg_app.start()

@app.on_event("shutdown")
async def shutdown():
    await tg_app.stop()
    await tg_app.shutdown()

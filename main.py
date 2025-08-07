from fastapi import FastAPI, Query, Header, HTTPException
from typing import List
from datetime import datetime
import httpx
import os

app = FastAPI()

# Environment Config
API_KEY = os.getenv("API_KEY")
NODO_API = os.getenv("NODO_API", "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt")
VAULT_ADDRESS = os.getenv("VAULT_ADDRESS")  # Required
MIN_TVL = float(os.getenv("MIN_TVL", 10))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Cache for already alerted wallets
notified_wallets = set()

# Send alert to Telegram
async def send_telegram_alert(wallet: str, tvl: float):
    message = (
        f"✅ New Eligible Wallet for Galxe\n\n"
        f"👛 Wallet: `{wallet}`\n"
        f"💰 TVL: ${tvl:,.2f}\n"
        f"🔗 Vault: https://ai.nodo.xyz/vault/{VAULT_ADDRESS}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

# For Galxe credential API
@app.get("/api/depositors")
async def get_valid_wallets(
    wallets: List[str] = Query(...),
    authorization: str = Header(None)
):
    if authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with httpx.AsyncClient() as client:
        response = await client.get(NODO_API)
        data = response.json()

    eligible = []

    for vault in data.get("data", []):
        if vault.get("address") == VAULT_ADDRESS:
            for wallet in wallets:
                user_data = vault.get("wallets", {}).get(wallet.lower())
                if user_data:
                    tvl = float(user_data.get("tvl", 0))
                    if tvl >= MIN_TVL:
                        if wallet.lower() not in notified_wallets:
                            await send_telegram_alert(wallet, tvl)
                            notified_wallets.add(wallet.lower())
                        eligible.append({
                            "id": wallet,
                            "timestamp": int(datetime.utcnow().timestamp())
                        })
            break

    return {"credential": eligible}

# Manual check route
@app.get("/check")
async def check_wallet(wallet: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(NODO_API)
        data = response.json()

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

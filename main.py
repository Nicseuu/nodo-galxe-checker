import os
import logging
import asyncio
from typing import List, Dict, Any

import httpx
import nest_asyncio
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Patch asyncio to work in hosted environments that reuse loops
nest_asyncio.apply()

# --------------------
# Config
# --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = -1002653992951
CHECK_INTERVAL_SECONDS = 300  # 5 minutes
DEPOSIT_THRESHOLD_USD = 100.0
HTTP_TIMEOUT_SECONDS = 12
NODO_API = "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt"

# --------------------
# Logging
# --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("nodo-bot")

# --------------------
# Vaults to monitor
# --------------------
VAULTS: List[Dict[str, Any]] = [
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

# --------------------
# Helpers
# --------------------
async def fetch_vaults() -> List[Dict[str, Any]]:
    """Fetch and normalize vault list from NODO API."""
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
            r = await client.get(NODO_API)
            r.raise_for_status()
            js = r.json()
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return []

    if isinstance(js, dict) and "data" in js:
        arr = js["data"]
    else:
        arr = js if isinstance(js, list) else []

    # Normalize address to lower for matching
    for v in arr:
        if isinstance(v, dict) and "address" in v and isinstance(v["address"], str):
            v["address"] = v["address"].lower()
    return arr

def find_vault(data: List[Dict[str, Any]], address: str) -> Dict[str, Any] | None:
    addr = address.lower()
    for v in data:
        if isinstance(v, dict) and v.get("address") == addr:
            return v
    return None

# --------------------
# Command Handlers
# --------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Bot is live.")

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Bot is running and monitoring vaults.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    parts = []
    for v in VAULTS:
        tvl = v.get("last_tvl")
        if tvl is None:
            parts.append(f"{v['name']}: not checked yet")
        else:
            parts.append(f"{v['name']}: ${tvl:,.2f}")
    await context.bot.send_message(chat_id, "\n".join(parts))

async def cmd_apy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = await fetch_vaults()
    if not data:
        await context.bot.send_message(chat_id, "API unavailable.")
        return

    lines = []
    for v in VAULTS:
        d = find_vault(data, v["address"])
        if not d:
            continue
        # support both shapes: d["apy"], d["tvl"] or nested dicts
        apy = d.get("apy")
        tvl = d.get("tvl")
        if isinstance(tvl, dict):
            tvl = tvl.get("value", 0)
        try:
            apy_val = float(apy) if apy is not None else 0.0
            tvl_val = float(tvl) if tvl is not None else 0.0
        except Exception:
            apy_val = 0.0
            tvl_val = 0.0
        lines.append(
            f"{v['platform']}: {v['name']}\n"
            f"APY: {apy_val:.2f}%\n"
            f"TVL: ${tvl_val:,.2f}\n"
            f"Link: {v['link']}"
        )
    text = "\n\n".join(lines) if lines else "No vault data."
    await context.bot.send_message(chat_id, text, disable_web_page_preview=False)

# --------------------
# Monitor job
# --------------------
async def monitor_job(context: ContextTypes.DEFAULT_TYPE):
    data = await fetch_vaults()
    if not data:
        return

    for v in VAULTS:
        d = find_vault(data, v["address"])
        if not d:
            continue
        tvl = d.get("tvl")
        if isinstance(tvl, dict):
            tvl = tvl.get("value", 0)
        try:
            new_tvl = float(tvl) if tvl is not None else 0.0
        except Exception:
            new_tvl = 0.0

        last = v.get("last_tvl")
        if last is not None:
            change = new_tvl - float(last)
            if change >= DEPOSIT_THRESHOLD_USD:
                msg = (
                    f"New deposit detected\n"
                    f"{v['platform']}: {v['name']}\n"
                    f"Amount: ${change:,.2f}\n"
                    f"New TVL: ${new_tvl:,.2f}\n"
                    f"Link: {v['link']}"
                )
                await context.bot.send_message(GROUP_ID, msg, disable_web_page_preview=False)
        v["last_tvl"] = new_tvl

# --------------------
# App bootstrap
# --------------------
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("apy", cmd_apy))

    # Register command list for clients
    await app.bot.set_my_commands([
        BotCommand("start", "Start bot"),
        BotCommand("check", "Check if bot is live"),
        BotCommand("status", "Vault tracking status"),
        BotCommand("apy", "Show APY and TVL"),
    ])

    # Schedule monitor with job queue
    app.job_queue.run_repeating(monitor_job, interval=CHECK_INTERVAL_SECONDS, first=5)

    logger.info("Starting polling")
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    asyncio.run(main())

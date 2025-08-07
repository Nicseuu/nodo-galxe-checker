import os
import asyncio
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
MIN_DEPOSIT = float(os.getenv("MIN_DEPOSIT", 10))

VAULTS = [
    {
        "name": "SUI-USDC",
        "source": "Momentum Vaults",
        "address": "0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb",
        "link": "https://ai.nodo.xyz/vault/0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb",
        "last_tvl": None,
    },
    {
        "name": "DEEP-SUI",
        "source": "Momentum Vaults",
        "address": "0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448",
        "link": "https://ai.nodo.xyz/vault/0x5da10fa39c1fc9b0bf62956211e1a15cf29d3c73ada439c7b57b61e34c106448",
        "last_tvl": None,
    },
    {
        "name": "WAL-SUI",
        "source": "Momentum Vaults",
        "address": "0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0",
        "link": "https://ai.nodo.xyz/vault/0x56a891d68d8f1eef31ff43333ae593a31474f062502cc28ee0e9b69cda1f95d0",
        "last_tvl": None,
    },
    {
        "name": "SUI-USDC",
        "source": "Cetus Vault",
        "address": "0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989",
        "link": "https://ai.nodo.xyz/vault/0xd0fe855b80e952c86e2e513e0f46f4cd906c8a95a955fc9ee31c6053ba127989",
        "last_tvl": None,
    },
]

API_URL = "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt"

async def fetch_vault_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(API_URL)
        return response.json()

async def check_deposits(application):
    try:
        data = await fetch_vault_data()
        for vault in VAULTS:
            info = next((v for v in data if v["address"] == vault["address"]), None)
            if not info:
                continue

            tvl = float(info.get("tvl", 0))
            name = vault["name"]
            source = vault["source"]

            if vault["last_tvl"] is None:
                vault["last_tvl"] = tvl
                continue

            change = tvl - vault["last_tvl"]

            if change >= MIN_DEPOSIT:
                msg = (
                    f"🚨 New Deposit Alert!\n"
                    f"{source}: *{name}*\n"
                    f"💸 Amount: `${change:,.2f}`\n"
                    f"📊 New TVL: `${tvl:,.2f}`\n"
                    f"🔗 [Open Vault]({vault['link']})"
                )
                await application.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=False)

            vault["last_tvl"] = tvl
    except Exception as e:
        print("Error checking vaults:", e)

async def periodic_check(application):
    while True:
        await check_deposits(application)
        await asyncio.sleep(60)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online and monitoring all 4 vaults.")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_deposits(context.application)
    await update.message.reply_text("✅ Manual check complete.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("check", check_command))

    asyncio.create_task(periodic_check(app))
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())

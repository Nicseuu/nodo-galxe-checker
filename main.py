from fastapi import FastAPI, Query, Header, HTTPException
from typing import List
import httpx
from datetime import datetime

app = FastAPI()

API_KEY = "your-secret-token"
NODO_API = "https://ai-api.nodo.xyz/data-management/ext/vaults?partner=mmt"
VAULT_ADDRESS = "0x72d394ff757d0b7795bb2ee5046aaeedcfc9c522f6565f8c0a4505670057e1eb"  # SUI-USDC vault
MIN_TVL = 10  # USD

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
                        eligible.append({
                            "id": wallet,
                            "timestamp": int(datetime.utcnow().timestamp())
                        })
            break

    return {"credential": eligible}

import httpx
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("JARVIS_API_URL")
API_TOKEN = os.getenv("JARVIS_API_TOKEN")

async def get_isolator_detail_df() ->pd.DataFrame:
    """
    Mengambil seluruh data DETAIL ISOLATOR dari API
    """

    url = f"{API_URL}/isolator"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json"}

    all_records = []
    page = 1
    per_page = 1000

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                url,
                headers=headers,
                params={
                    "page": page,
                    "per_page": per_page},
                    timeout=30)

            response.raise_for_status()
            result = response.json()
            records = result.get("data", [])

            if records:
                all_records.extend(records)

            pagination = result.get("pagination", {})
            if not pagination.get("next_page", False):
                break

            page += 1

    if not all_records:
        return pd.DataFrame()

    return pd.DataFrame(all_records)
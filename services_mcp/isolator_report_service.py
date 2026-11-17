import pandas as pd
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("JARVIS_API_URL")
API_TOKEN = os.getenv("JARVIS_API_TOKEN")

async def get_isolator_report_df() -> dict[str, pd.DataFrame]:
    """
    Mengambil data RANGKUMAN ISOLATOR dari API
    dan mengembalikan setiap kategori sebagai DataFrame
    """

    url = f"{API_URL}/isolator-report"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()
        data = result.get("data", {})

        if not data:
            return {}

        return {
            category: pd.DataFrame(records)
            for category, records in data.items()
        }
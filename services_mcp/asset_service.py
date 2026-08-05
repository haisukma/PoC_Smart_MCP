import os
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")

async def get_asset():
    """
    Mengambil data asset dari API.
    """

    url = f"{API_BASE_URL}/asset"

    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        assets = result.get("data", [])

        cleaned_assets = [
            {
                key: value
                for key, value in asset.items()
                if key not in ["id", "created_at"]
            }
            for asset in assets
        ]

        return cleaned_assets

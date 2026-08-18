import os
import httpx
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL")

async def get_asset_df() -> pd.DataFrame:
    """
    Mengambil data asset dari API dan mengembalikannya sebagai Pandas DataFrame.
    """
    url = f"{API_BASE_URL}/asset"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30)
        response.raise_for_status()
        result = response.json()
        data_sales = result.get("data", [])

        if not data_sales:
            return pd.DataFrame()

        df = pd.DataFrame(data_sales)

        drop_cols = [col for col in ["id", "created_at"] if col in df.columns]
        if drop_cols:
            df = df.drop(columns=drop_cols)

        return df
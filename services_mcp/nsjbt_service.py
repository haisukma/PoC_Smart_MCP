import os
import httpx
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv(
    "NSJBT_API_BASE_URL"
)

API_ACCESS_TOKEN = os.getenv("NSJBT_API_ACCESS_TOKEN")

async def get_master2_rows():
    """
    Mengambil data master2 dari API NSJBT.
    """

    if not API_ACCESS_TOKEN:
        raise ValueError(
            "NSJBT_API_ACCESS_TOKEN belum diset"
        )

    url = f"{API_BASE_URL}/master2/row/"

    headers = {
        "Authorization": f"Bearer {API_ACCESS_TOKEN}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        rows_data = []

        for item in data:

            rows = item.get(
                "ROWS",
                []
            )

            if rows:

                rows_data.extend(
                    rows
                )

        return rows_data

async def summarize_master2_rows():
    """
    Mengambil data master2 dari API NSJBT
    dan membuat ringkasan atau kesimpulan statistik.
    """

    data = await get_master2_rows()

    total_idloc = len(data)

    total_rows = 0

    row_types = Counter()
    owners = Counter()
    statuses = Counter()
    data_statuses = Counter()

    for item in data:

        rows = item.get(
            "ROWS",
            []
        )

        total_rows += len(rows)

        for row in rows:
            row_type = row.get(
                "ROWTYPENAME"
            )

            if row_type:
                row_types[row_type] += 1

            owner = row.get(
                "OWNER"
            )

            if owner:
                owners[owner] += 1

            status = row.get(
                "STATUS"
            )

            if status:
                statuses[status] += 1

            data_status = row.get(
                "DATASTATUS"
            )

            if data_status:
                data_statuses[data_status] += 1

    return {
        "total_idloc": total_idloc,
        "total_rows": total_rows,
        "row_types": dict(
            row_types
        ),
        "owners": dict(
            owners
        ),
        "statuses": dict(
            statuses
        ),
        "data_statuses": dict(
            data_statuses
        )
    }

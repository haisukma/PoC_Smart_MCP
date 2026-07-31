import json

JSON_FILE = "coinmarketcap_data.json"

async def get_cryptocurrency_data():

    try:

        with open(
            JSON_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        return data


    except FileNotFoundError:

        return {
            "error": (
                f"File {JSON_FILE} "
                "tidak ditemukan."
            )
        }


    except json.JSONDecodeError:

        return {
            "error": (
                f"File {JSON_FILE} "
                "bukan JSON yang valid."
            )
        }
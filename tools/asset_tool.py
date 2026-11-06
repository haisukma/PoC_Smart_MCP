import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.asset_service import get_asset_df

_ASSET_DF: pd.DataFrame = None

async def _get_cached_asset_df() -> pd.DataFrame:
    global _ASSET_DF
    if _ASSET_DF is None or _ASSET_DF.empty:
        _ASSET_DF = await get_asset_df()
    return _ASSET_DF

def register_asset_tools(mcp):

    @mcp.tool()
    async def execute_asset_python_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data Asset dari API
        Mengeksekusi kode Python pada variabel `df` (Pandas DataFrame sales)

        Args:
            code: Kode Python yang akan dieksekusi. WAJIB menggunakan print(...) untuk melihat output!
                  Contoh: print(df[df['region'].str.lower() == 'bandung'])
        """
        try:
            df = await _get_cached_asset_df()
            if df.empty:
                return "Data asset dari API kosong"

            safe_builtins = {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round
            }

            safe_globals = {
                "__builtins__": safe_builtins,
                "pd": pd,
                "np": np,
                "json": json,
                "datetime": datetime
            }

            local_vars_asset = {"df": df, "pd": pd}
            output_buffer_asset = io.StringIO()

            with contextlib.redirect_stdout(output_buffer_asset):
                exec(code, safe_globals, local_vars_asset)

            result = output_buffer_asset.getvalue()
            return result if result.strip() else "Kode berhasil dieksekusi tanpa output print"

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

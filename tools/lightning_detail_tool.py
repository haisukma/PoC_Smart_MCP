import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.lightning_detail_service import get_lightning_detail_df

LIGHTNING_DETAIL_DF = None

async def _get_cached_lightning_detail_df() -> pd.DataFrame:
    global LIGHTNING_DETAIL_DF

    if LIGHTNING_DETAIL_DF is None or LIGHTNING_DETAIL_DF.empty:
        LIGHTNING_DETAIL_DF = await get_lightning_detail_df()

    return LIGHTNING_DETAIL_DF

def register_lightning_detail_tools(mcp):

    @mcp.tool()
    async def execute_lightning_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL PENAMBAHAN PROTEKSI PETIR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_lightning = await _get_cached_lightning_detail_df()
            if df_lightning.empty:
                return "Data lightning report kosong"

            local_vars = {
                "df": df_lightning,
                "pd": pd
            }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except Exception as e:
            return f"Error executing Python code: {str(e)}"
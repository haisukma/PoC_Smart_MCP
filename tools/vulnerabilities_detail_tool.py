import io
import contextlib
import pandas as pd
import numpy as np
from services_mcp.vulnerabilities_detail_service import get_vulnerabilities_detail_df

VULNERABILITIES_DETAIL_DF = None

async def _get_cached_vulnerabilities_detail_df() -> pd.DataFrame:
    global VULNERABILITIES_DETAIL_DF

    if VULNERABILITIES_DETAIL_DF is None or VULNERABILITIES_DETAIL_DF.empty:
        VULNERABILITIES_DETAIL_DF = await get_vulnerabilities_detail_df()

    return VULNERABILITIES_DETAIL_DF

def register_vulnerabilities_detail_tools(mcp):

    @mcp.tool()
    async def execute_vulnerabilities_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL VULNERABILITIES atau POTENSI KERAWANAN JALUR TRANSMISI
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_vulnerabilities = await _get_cached_vulnerabilities_detail_df()
            if df_vulnerabilities.empty:
                return "Data vulnerabilities detail kosong"

            local_vars = {
                "df": df_vulnerabilities,
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
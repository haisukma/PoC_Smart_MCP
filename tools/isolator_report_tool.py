import io
import contextlib
import pandas as pd
import numpy as np
import json
from services_mcp.isolator_report_service import get_isolator_report_df

__ISOLATOR_REPORT_DF: pd.DataFrame = None

async def _get_cached_isolator_report_df() -> dict[str, pd.DataFrame]:
    global __ISOLATOR_REPORT_DF

    if __ISOLATOR_REPORT_DF is None or not __ISOLATOR_REPORT_DF:
        __ISOLATOR_REPORT_DF = await get_isolator_report_df()

    return __ISOLATOR_REPORT_DF

def register_isolator_report_tools(mcp):

    @mcp.tool()
    async def execute_isolator_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data ISOLATOR REPORT/KESIMPULAN ISOLATOR dari API
        
        DataFrame yang tersedia:
        - df_realisasi_total: Data isolator berdasarkan realisasi total
        - df_realiasi_tower: Data isolator berdasarkan realisasi tower
        
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            isolator_data = await _get_cached_isolator_report_df()
            if not isolator_data:
                return "Data isolator report dari API kosong"

            local_vars = {
                "df_realisasi_total": isolator_data["realisasi_total"],
                "df_relisasi_tower": isolator_data["realisasi_tower"],
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

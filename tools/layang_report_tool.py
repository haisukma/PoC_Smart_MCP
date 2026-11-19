import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.layang_report_service import get_layang_report_df

__LAYANG_REPORT_DF: pd.DataFrame = None

async def _get_cached_layang_report_df() -> dict[str, pd.DataFrame]:
    global __LAYANG_REPORT_DF

    if __LAYANG_REPORT_DF is None or not __LAYANG_REPORT_DF:
        __LAYANG_REPORT_DF = await get_layang_report_df()

    return __LAYANG_REPORT_DF

def register_layang_report_tools(mcp):

    @mcp.tool()
    async def execute_layang_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data AGREGASI atau KESIMPULAN LAYANG-LAYANG dari API

        DataFrame yang tersedia:
        - df_inspection_map: Data rekap peta inspeksi
        - df_mitigation_layang: Data penurunan layangan dan mitigasi benda asing

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            layang_report_data = await _get_cached_layang_report_df()
            if not layang_report_data:
                return "Data layang report dari API kosong"

            local_vars = {
                "df_inspection_map": layang_report_data["inspection_map"],
                "df_mitigation_layang": layang_report_data["mitigation_layang"],
                "pd": pd}

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(code, local_vars)

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print")

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

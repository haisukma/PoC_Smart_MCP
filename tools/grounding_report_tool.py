import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.grounding_report_service import get_grounding_report_df

__GROUNDING_REPORT_DF: pd.DataFrame = None

async def _get_cached_grounding_report_df() -> dict[str, pd.DataFrame]:
    global __GROUNDING_REPORT_DF

    if __GROUNDING_REPORT_DF is None or not __GROUNDING_REPORT_DF:
        __GROUNDING_REPORT_DF = await get_grounding_report_df()

    return __GROUNDING_REPORT_DF

def register_grounding_report_tools(mcp):

    @mcp.tool()
    async def execute_grounding_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data GROUNDING REPORT/KESIMPULAN GROUNDING dari API

        DataFrame yang tersedia:
        - df_target: Data target dan realisasi per UPT
        - df_prosentase: Data persentase status grounding
        - df_proteksi: Data kondisi proteksi tambahan
        - df_leg: Data kondisi leg

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            grounding_data = await _get_cached_grounding_report_df()
            if not grounding_data:
                return "Data grounding report dari API kosong"

            local_vars = {
                "df_target": grounding_data["target_realisasi"],
                "df_prosentase": grounding_data["prosentase"],
                "df_proteksi": grounding_data["proteksi"],
                "df_leg": grounding_data["leg"],
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

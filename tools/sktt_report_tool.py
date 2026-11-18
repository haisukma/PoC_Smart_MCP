import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.sktt_report_service import get_sktt_report_df

__SKTT_REPORT_DF: pd.DataFrame = None

async def _get_cached_sktt_report_df() -> dict[str, pd.DataFrame]:
    global __SKTT_REPORT_DF

    if __SKTT_REPORT_DF is None or not __SKTT_REPORT_DF:
        __SKTT_REPORT_DF = await get_sktt_report_df()

    return __SKTT_REPORT_DF

def register_sktt_report_tools(mcp):

    @mcp.tool()
    async def execute_sktt_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data SUMMARY atau RANGKUMAN SALURAN KABEL TEGANGAN TINGGI dari API

        DataFrame yang tersedia:
        - df_real_join: Data realisasi dan target IL3 JOINT SKTT per UPT item SKTT
        - df_insulation_issues: Data rekap tahanan isolasi buruk (>standar) item SKTT
        - df_high_leakage: Data rekap arus bocor tinggi (>standar) di item SKTT

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            sktt_report_data = await _get_cached_sktt_report_df()
            if not sktt_report_data:
                return "Data sktt report dari API kosong"

            local_vars = {
                "df_real_join": sktt_report_data["real_join"],
                "df_insulation_issues": sktt_report_data["insulation_issues"],
                "df_high_leakage": sktt_report_data["high_leakage"],
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

import io
import contextlib
import pandas as pd
import numpy as np
import json
import datetime
from services_mcp.jumper_gsw_report_service import get_jumper_gsw_report_df

__JUMPER_GSW_REPORT_DF: pd.DataFrame = None

async def _get_cached_jumper_gsw_report_df() -> dict[str, pd.DataFrame]:
    global __JUMPER_GSW_REPORT_DF

    if __JUMPER_GSW_REPORT_DF is None or not __JUMPER_GSW_REPORT_DF:
        __JUMPER_GSW_REPORT_DF = await get_jumper_gsw_report_df()

    return __JUMPER_GSW_REPORT_DF

def register_jumper_gsw_report_tools(mcp):

    @mcp.tool()
    async def execute_jumper_gsw_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data JUMPER GSW REPORT/KESIMPULAN JUMPER GSW dari API

        DataFrame yang tersedia:
        - df_assesment_execution: Data target dan realisasi pelaksana asesmen per UPT item jumper
        - df_assesment_visual: Data hasil assesmen visual item jumper
        - df_above_standard: Data jumper gsw yang lebih dari standar

        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            jumper_report_data = await _get_cached_jumper_gsw_report_df()
            if not jumper_report_data:
                return "Data jumper gsw report dari API kosong"

            local_vars = {
                "df_assesment_execution": jumper_report_data["assesment_execution"],
                "df_assesment_visual": jumper_report_data["assesment_visual"],
                "df_above_standard": jumper_report_data["above_standard"],
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

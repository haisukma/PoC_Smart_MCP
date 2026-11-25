import pandas as pd
import io
import contextlib
from services_mcp.isolator_change_report_service import get_isolator_change_report_df

__ISOLATOR_CHANGE_REPORT_DF: pd.DataFrame = None

async def _get_cached_isolator_change_report_df() -> dict[str, pd.DataFrame]:
    global __ISOLATOR_CHANGE_REPORT_DF

    if __ISOLATOR_CHANGE_REPORT_DF is None or not __ISOLATOR_CHANGE_REPORT_DF:
        __ISOLATOR_CHANGE_REPORT_DF = await get_isolator_change_report_df()

    return __ISOLATOR_CHANGE_REPORT_DF

def register_isolator_change_report_tools(mcp):

    @mcp.tool()
    async def execute_isolator_change_report_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data LAPORAN AGREGASI atau SUMMARY PENGGANTIAN ISOLATOR
        
        DataFrame yang tersedia:
        - df_realisasi_change: Data realisasi penggantian isolator per UPT
        - df_type_change: Data tipe penggantian isolator per UPT
        
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            isolator_change_report_data = await _get_cached_isolator_change_report_df()
            if not isolator_change_report_data:
                return "Data isolator change report dari API kosong"

            local_vars = {
                "df_realisasi_change": isolator_change_report_data["realisasi_change"],
                "df_type_change": isolator_change_report_data["type_change"]
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
            return f"Error executing python code: {str(e)}"
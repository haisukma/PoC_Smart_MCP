import io
import contextlib
import pandas as pd
import numpy as np
from e2b_code_interpreter import AsyncSandbox
import textwrap
from services_mcp.corona_detail_service import get_corona_detail_df

CORONA_DETAIL_DF = None

async def _get_cached_corona_detail_df() -> pd.DataFrame:
    global CORONA_DETAIL_DF

    if CORONA_DETAIL_DF is None or CORONA_DETAIL_DF.empty:
        CORONA_DETAIL_DF = await get_corona_detail_df()

    return CORONA_DETAIL_DF

def register_corona_detail_tools(mcp):

    @mcp.tool()
    async def execute_corona_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL KORONA PADA TRANSMISI menggunakan E2B Sandbox
        
        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        
        Eksekusi Python dilakukan di lingkungan sandbox terisolasi
        """

        sandbox = None
        try:
            df_corona = await _get_cached_corona_detail_df()

            if df_corona.empty:
                return "Data detail korona kosong"

            json_data = df_corona.to_json(orient="records")
            json_path = "/tmp/korona_detail.json"

            sandbox = await AsyncSandbox.create()
            await sandbox.files.write(json_path, json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd
                df = pd.read_json("{json_path}", orient="records")
                print("Shape: ", df.shape)
                print("Columns: ", df.columns.tolist)
            """) + "\n" + textwrap.dedent(code)

            execution = await sandbox.run_code(
                execution_code, timeout=120
            )

            if execution.error:
                return (
                    "Error executing Python code:"
                    f"{execution.error.value}"
                )

            stdout = execution.logs.stdout or []
            result = "".join(str(item) for item in stdout)

            return(
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

        finally:
            if sandbox is not None:
                try:
                    await sandbox.kill()
                except Exception:
                    pass

# def register_corona_detail_tools(mcp):

#     @mcp.tool()
#     async def execute_corona_detail_analysis(code: str) -> str:
#         """
#         Mengambil data mentah (DataFrame) DETAIL KORONA PADA TRANSMISI.
#         WAJIB dipanggil PERTAMA kali untuk pertanyaan detail korona, 
#         sebelum memanggil `execute_corona_detail_analysis`
#         """

#         try:
#             df_corona = await _get_cached_corona_detail_df()
#             if df_corona.empty:
#                 return "Data corona report kosong"

#             local_vars = {
#                 "df": df_corona,
#                 "pd": pd
#             }

#             output_buffer = io.StringIO()
#             with contextlib.redirect_stdout(output_buffer):
#                 exec(code, local_vars)

#             result = output_buffer.getvalue()

#             return (
#                 result.strip()
#                 if result.strip()
#                 else "Kode berhasil dieksekusi tanpa output print"
#             )

#         except Exception as e:
#             return f"Error executing Python code: {str(e)}"
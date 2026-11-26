import pandas as pd
import numpy as np
import textwrap
import io
import contextlib
from e2b_code_interpreter import AsyncSandbox
from services_mcp.arching_horn_detail_service import get_arching_horn_detail_df

ARCHING_HORN_DETAIL_DF = None

async def _get_cached_arching_horn_detail_df() -> pd.DataFrame:
    global ARCHING_HORN_DETAIL_DF

    if ARCHING_HORN_DETAIL_DF is None or ARCHING_HORN_DETAIL_DF.empty:
        ARCHING_HORN_DETAIL_DF = await get_arching_horn_detail_df()

    return ARCHING_HORN_DETAIL_DF

# def register_arching_horn_detail_tools(mcp):

#     @mcp.tool()
#     async def execute_arching_horn_detail_analysis(code: str) -> str:
#         """
#         Menganalisis data DETAIL ARCHING HORN menggunakan E2B Sandbox
        
#         DataFrame tersedia dalam variabel df
#         WAJIB menggunakan print(...) untuk melihat output
        
#         Ekseskusi Python dilakukan di lingkungan sandbox terisolasi
#         """

#         sandbox = None
#         try:
#             df_arching_horn = await _get_cached_arching_horn_detail_df()

#             if df_arching_horn.empty:
#                 return "Data detail arching horn kosong"

#             json_data = df_arching_horn.to_json(orient="records")
#             json_path = "/tmp/arching_horn_detail.json"

#             sandbox = await AsyncSandbox.create()
#             await sandbox.files.write(json_path, json_data)

#             execution_code = textwrap.dedent(f"""
#                 import pandas as pd
#                 df = pd.read_json("{json_path}", orient="records")
#                 print("Shape:", df.shape)
#                 print("Columns:", df.columns.tolist)
#             """) + "\n" + textwrap.dedent(code)

#             execution = await sandbox.run_code(
#                 execution_code, timeout=120)

#             if execution.error:
#                 return(
#                     "Error executing Python code: "
#                     f"{execution.error.values}"
#                 )

#             stdout = execution.logs.stdout or []
#             result = "".join(str(item) for item in stdout)

#             return(
#                 result.strip()
#                 if result.strip()
#                 else "Kode berhasil dieksekusi tanpa output print"
#             )

#         except Exception as e:
#             return f"Error executing Python code: {str(e)}"

#         finally:
#             if sandbox is not None:
#                 try:
#                     await sandbox.kill()
#                 except Exception:
#                     pass

def register_arching_horn_detail_tools(mcp):

    @mcp.tool()
    async def execute_arching_horn_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL ARCHING_HORN
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            df_arching_horn = await _get_cached_arching_horn_detail_df()
            if df_arching_horn.empty:
                return "Data arching horn report kosong"

            local_vars = {
                "df": df_arching_horn,
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
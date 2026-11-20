import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
from e2b_code_interpreter import AsyncSandbox
from services_mcp.isolator_clean_service import get_isolator_clean_df

ISOLATOR_CLEAN_DF = None

async def _get_cached_isolator_clean_df() -> pd.DataFrame:
    global ISOLATOR_CLEAN_DF

    if ISOLATOR_CLEAN_DF is None or ISOLATOR_CLEAN_DF.empty:
        ISOLATOR_CLEAN_DF = await get_isolator_clean_df()

    return ISOLATOR_CLEAN_DF

def register_isolator_clean_tools(mcp):

    @mcp.tool()
    async def execute_isolator_clean_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL PEMBERSIHAN ISOLATOR menggunakan E2B Sandbox
        
        DataFrame tersedia dalam variabel df
        WAJIB menggunakan print(...) untuk melihat output
        
        Eksekusi Python dilakukan di lingkungan sandbox terisolasi
        """

        sandbox = None
        try:
            df_isolator_clean = await _get_cached_isolator_clean_df()

            if df_isolator_clean.empty:
                return "Data detail pembersihan isolator kosong"

            json_data = df_isolator_clean.to_json(orient="records")
            json_path = "/tmp/isolator_clean_detail.json"

            sandbox = await AsyncSandbox.create()
            await sandbox.files.write(json_path, json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd
                df = pd.read_json("{json_path}", orient="records")
                print("SHAPE: ", df.shape)
                print("COLUMNS: ", df.columns.tolist)
            """) + "\n" + textwrap.dedent(code)

            execution = await sandbox.run_code(
                execution_code, temieout=120
            )

            if execution.error:
                return(
                    "Error executing Python code: "
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

# def register_isolator_clean_tools(mcp):

#     @mcp.tool()
#     async def execute_isolator_clean_analysis(code: str) -> str:
#         """
#         Gunakan tool ini untuk menganalisis data DETAIL PEMBERSIHAN ISOLATOR
        
#         DataFrame tersedia dalam variabel df.
#         WAJIB menggunakan print(...) untuk melihat output
#         """

#         try:
#             df_isolator_clean = await _get_cached_isolator_clean_df()
#             if df_isolator_clean.empty:
#                 return "Data grounding report kosong"

#             local_vars_isolator = {
#                 "df": df_isolator_clean,
#                 "pd": pd
#             }

#             output_buffer = io.StringIO()
#             with contextlib.redirect_stdout(output_buffer):
#                 exec(code, local_vars_isolator)

#             result = output_buffer.getvalue()

#             return (
#                 result.strip()
#                 if result.strip()
#                 else "Kode berhasil dieksekusi tanpa output print")

#         except Exception as e:
#             return f"Error executing Python Code: {str(e)}"            
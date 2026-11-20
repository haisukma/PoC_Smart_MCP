import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
from e2b_code_interpreter import AsyncSandbox
from services_mcp.grounding_detail_service import get_grounding_detail_df

GROUNDING_DETAIL_DF = None

async def _get_cached_grounding_detail_df() -> pd.DataFrame:
    global GROUNDING_DETAIL_DF

    if GROUNDING_DETAIL_DF is None or GROUNDING_DETAIL_DF.empty:
        GROUNDING_DETAIL_DF = await get_grounding_detail_df()

    return GROUNDING_DETAIL_DF

# def register_grounding_detail_tools(mcp):

#     @mcp.tool()
#     async def execute_grounding_detail_analysis(code: str) -> str:
#         """
#         Gunakan tool ini untuk menganalisis data DETAIL GROUNDING

#         DataFrame tersedia dalam variabel df
#         WAJIB menggunakan print(...) untuk melihat output
#         """

#         try:
#             df_grounding = await _get_cached_grounding_detail_df()

#             if df_grounding.empty:
#                 return "Data grounding report kosong"

#             local_vars_grounding = {
#                 "df": df_grounding,
#                 "pd": pd
#             }

#             output_buffer = io.StringIO()
#             with contextlib.redirect_stdout(output_buffer):
#                 exec(code, local_vars_grounding)

#             result = output_buffer.getvalue()

#             return (
#                 result.strip()
#                 if result.strip()
#                 else "Kode berhasil dieksekusi tanpa output print")

#         except Exception as e:
#             return f"Error executing Python code: {str(e)}"

def register_grounding_detail_tools(mcp):

    @mcp.tool()
    async def execute_grounding_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL GROUNDING menggunakan E2B Sandbox.

        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output.

        Eksekusi Python dilakukan di lingkungan sandbox terisolasi.
        """

        sandbox = None

        try:
            df_grounding = await _get_cached_grounding_detail_df()

            if df_grounding.empty:
                return "Data detail grounding kosong"

            json_data = df_grounding.to_json(orient="records")

            sandbox = await AsyncSandbox.create()
            json_path = "/tmp/grounding_detail.json"

            await sandbox.files.write(json_path, json_data)

            execution_code = textwrap.dedent(f"""
                import pandas as pd

                df = pd.read_json("{json_path}", orient="records")

                print("Shape:", df.shape)
                print("Columns:", df.columns.tolist())

            """) + "\n" + textwrap.dedent(code)

            execution = await sandbox.run_code(
                execution_code,
                timeout=120)

            if execution.error:
                return (
                    "Error executing Python code: "
                    f"{execution.error.value}"
                )

            stdout = execution.logs.stdout or []
            result = "".join(str(item) for item in stdout)

            return (
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

import io
import contextlib
import pandas as pd
import numpy as np
import textwrap
import modal
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

    MODAL_IMAGE = modal.Image.debian_slim(python_version="3.12").pip_install(
        "pandas",
        "numpy",
        "matplotlib",
        "seaborn",
    )
    MODAL_APP = modal.App.lookup("si-smart-sandbox", create_if_missing=True)

    @mcp.tool()
    async def execute_grounding_detail_analysis(code: str) -> str:
        """
        Menganalisis data DETAIL GROUNDING menggunakan Modal Sandbox.

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
            sandbox = await modal.Sandbox.create.aio(
                image=MODAL_IMAGE,
                app=MODAL_APP,
                region=["ap-southeast"],
                cpu=0.25,
                memory=512,
                timeout=120,
                block_network=True,
            )
            json_path = "/tmp/grounding_detail.json"
            async with sandbox.open.aio(json_path, "w") as f:
                await f.write.aio(json_data)

            execution_code = (
                textwrap.dedent(f"""
                    import pandas as pd

                    df = pd.read_json("{json_path}", orient="records")

                    print("Shape:", df.shape)
                    print("Columns:", df.columns.tolist())

                """)
                + "\n"
                + textwrap.dedent(code)
            )

            process = await sandbox.exec.aio("python", "-c", execution_code)
            stdout = await process.stdout.read.aio()
            stderr = await process.stderr.read.aio()
            await process.wait.aio()

            if process.returncode != 0:
                return (
                    "Error executing Python code: "
                    f"{stderr.strip()}"
                )

            return (
                stdout.strip()
                if stdout.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except Exception as e:
            return f"Error executing Python code: {str(e)}"

        finally:
            if sandbox is not None:
                try:
                    await sandbox.terminate.aio()
                except Exception:
                    pass

    # @mcp.tool()
    # async def execute_grounding_detail_analysis(code: str) -> str:
    #     """
    #     Menganalisis data DETAIL GROUNDING menggunakan E2B Sandbox.

    #     DataFrame tersedia dalam variabel df.
    #     WAJIB menggunakan print(...) untuk melihat output.

    #     Eksekusi Python dilakukan di lingkungan sandbox terisolasi.
    #     """

    #     sandbox = None

    #     try:
    #         df_grounding = await _get_cached_grounding_detail_df()

    #         if df_grounding.empty:
    #             return "Data detail grounding kosong"

    #         json_data = df_grounding.to_json(orient="records")

    #         sandbox = await AsyncSandbox.create()
    #         json_path = "/tmp/grounding_detail.json"

    #         await sandbox.files.write(json_path, json_data)

    #         execution_code = textwrap.dedent(f"""
    #             import pandas as pd

    #             df = pd.read_json("{json_path}", orient="records")

    #             print("Shape:", df.shape)
    #             print("Columns:", df.columns.tolist())

    #         """) + "\n" + textwrap.dedent(code)

    #         execution = await sandbox.run_code(
    #             execution_code,
    #             timeout=120)

    #         if execution.error:
    #             return (
    #                 "Error executing Python code: "
    #                 f"{execution.error.value}"
    #             )

    #         stdout = execution.logs.stdout or []
    #         result = "".join(str(item) for item in stdout)

    #         return (
    #             result.strip()
    #             if result.strip()
    #             else "Kode berhasil dieksekusi tanpa output print"
    #         )

    #     except Exception as e:
    #         return f"Error executing Python code: {str(e)}"

    #     finally:
    #         if sandbox is not None:
    #             try:
    #                 await sandbox.kill()
    #             except Exception:
    #                 pass

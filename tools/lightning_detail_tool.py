import io
import builtins
import contextlib
import pandas as pd
import numpy as np
from services_mcp.lightning_detail_service import get_lightning_detail_df
from guardrails.execution_policy import get_restricted_builtins, validate_code

LIGHTNING_DETAIL_DF = None

async def _get_cached_lightning_detail_df() -> pd.DataFrame:
    global LIGHTNING_DETAIL_DF

    if LIGHTNING_DETAIL_DF is None or LIGHTNING_DETAIL_DF.empty:
        LIGHTNING_DETAIL_DF = await get_lightning_detail_df()

    return LIGHTNING_DETAIL_DF

def register_lightning_detail_tools(mcp):

    @mcp.tool()
    async def execute_lightning_detail_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data DETAIL PENAMBAHAN PROTEKSI PETIR
        
        DataFrame tersedia dalam variabel df.
        WAJIB menggunakan print(...) untuk melihat output
        """

        try:
            validate_code(code)

            df_lightning = await _get_cached_lightning_detail_df()
            if df_lightning.empty:
                return "Data lightning report kosong"

            if not code or not code.strip():
                return "Kode Python tidak boleh kosong"

            df_execution = df_lightning.copy(deep=True)
            execution_globals = {
                "__builtins__": get_restricted_builtins(),
                "__name__": "__llm_analysis__",
                "df": df_execution,
                "pd": pd,
                "np": np
            }

            output_buffer = io.StringIO()
            with contextlib.redirect_stdout(output_buffer):
                exec(
                    compile(code, "<llm_generated_code>", "exec"),
                    execution_globals,
                    execution_globals
                )

            result = output_buffer.getvalue()

            return (
                result.strip()
                if result.strip()
                else "Kode berhasil dieksekusi tanpa output print"
            )

        except ImportError as e:
            return f"Library tidak diizinkan: {str(e)}"

        except Exception as e:
            return f"Error executing Python code: {str(e)}"
        
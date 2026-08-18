import io
import contextlib
import pandas as pd
from services_mcp.asset_service import get_asset_df

_ASSET_DF: pd.DataFrame = None

async def _get_cached_asset_df() -> pd.DataFrame:
    global _ASSET_DF
    if _ASSET_DF is None or _ASSET_DF.empty:
        _ASSET_DF = await get_asset_df()
    return _ASSET_DF

def register_asset_tools(mcp):

    @mcp.tool()
    async def execute_asset_python_analysis(code: str) -> str:
        """
        Gunakan tool ini untuk menganalisis data Asset dari API.
        Mengeksekusi kode Python pada variabel `df` (Pandas DataFrame sales).

        Args:
            code: Kode Python yang akan dieksekusi. WAJIB menggunakan print(...) untuk melihat output!
                  Contoh: print(df[df['region'].str.lower() == 'bandung'])
        """
        try:
            df = await _get_cached_asset_df()
            if df.empty:
                return "Data asset dari API kosong."

            local_vars = {"df": df, "pd": pd}
            output_buffer = io.StringIO()

            with contextlib.redirect_stdout(output_buffer):
                exec(code, {}, local_vars)

            result = output_buffer.getvalue()
            return result if result.strip() else "Kode berhasil dieksekusi tanpa output print."

        except Exception as e:
            return f"Error executing Python code: {str(e)}"
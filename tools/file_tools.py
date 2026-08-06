import io
from pathlib import Path
import sys
import pandas as pd
from pypdf import PdfReader

DATA_DIR = Path("data_storage")

def register_file_tools(mcp):

    @mcp.tool()
    async def get_dataset_schema(filename: str) -> str:
        """
        Mengambil skema file (kolom & sampel data untuk CSV/Excel) atau isi teks dokumen (untuk PDF).
        Gunakan tool ini PERTAMA KALI saat pengguna mengunggah file.

        PERINGATAN STRICT:
        - DILARANG dipanggil untuk data API (Sales Performance, Asset, Customer).
        - HANYA dipanggil jika ada argumen `filename` file yang diunggah.
        """
        filepath = DATA_DIR / filename
        if not filepath.exists():
            return f"Error: File '{filename}' tidak ditemukan di folder data_storage."

        suffix = filepath.suffix.lower()
        try:
            if suffix == ".csv":
                df_sample = pd.read_csv(filepath, nrows=5, low_memory=False)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    total_rows = sum(1 for _ in f) - 1
            elif suffix in [".xlsx", ".xls"]:
                df_sample = pd.read_excel(filepath, nrows=5)
                total_rows = "Banyak (Excel File)"

            elif suffix == ".pdf":
                reader = PdfReader(filepath)
                text = f"File Name: {filename} (Dokumen PDF)\nTotal Halaman: {len(reader.pages)}\n\n--- Isi Teks Dokumen ---\n"

                for i, page in enumerate(reader.pages[:15]):
                    text += f"\n[Halaman {i+1}]\n" + (page.extract_text() or "")
                
                return text if text.strip() else "File PDF berhasil dibaca, tetapi tidak ada teks yang terekstrak."

            else:
                return f"Error: Format file '{suffix}' belum didukung."

            output = []
            output.append(f"File Name: {filename}")
            output.append(f"Estimasi Total Baris: {total_rows}, Total Kolom: {len(df_sample.columns)}")
            output.append("\nDaftar Nama Kolom & Tipe Data:")
            for col, dtype in df_sample.dtypes.items():
                output.append(f"- '{col}' ({dtype})")

            output.append("\nSample Data (5 baris pertama):")
            output.append(df_sample.to_string(index=False))

            return "\n".join(output)

        except Exception as e:
            return f"Error saat membaca skema/isi file: {str(e)}"

    @mcp.tool()
    async def execute_python_analysis(filename: str, python_code: str) -> str:
        """
        Menjalankan kode Python Pandas untuk menganalisis data CSV atau Excel.

        CATATAN PENTING UNTUK LLM:
        - Tool ini HANYA untuk file CSV/Excel! DILARANG digunakan untuk file PDF.
        - Variabel `df` SUDAH DILOAD secara otomatis. JANGAN menulis `df = pd.read_csv(...)` lagi!
        - Langsung manipulasi variabel `df` yang tersedia, lalu WAJIB gunakan `print(...)`.
        """
        filepath = DATA_DIR / filename
        if not filepath.exists():
            return f"Error: File '{filename}' tidak ditemukan di folder data_storage."

        suffix = filepath.suffix.lower()

        if suffix == ".pdf":
            return (
                f"Error: File '{filename}' adalah file PDF. "
                "Fungsi execute_python_analysis hanya untuk file tabular (CSV/Excel). "
                "Gunakan teks yang sudah didapatkan dari get_dataset_schema untuk menjawab pertanyaan pengguna."
            )

        try:
            if suffix == ".csv":
                df = pd.read_csv(filepath, low_memory=False)
            elif suffix in [".xlsx", ".xls"]:
                df = pd.read_excel(filepath)
            else:
                return f"Error: Format file '{suffix}' tidak didukung untuk analisis Pandas."

            original_stdout = sys.stdout
            buffer = io.StringIO()
            sys.stdout = buffer

            local_vars = {
                "df": df,
                "pd": pd,
                "filepath": str(filepath)
            }

            exec(python_code, {}, local_vars)

            result = buffer.getvalue()
            return result if result.strip() else "Kode berhasil dieksekusi, tetapi tidak ada output print(). Pastikan menggunakan print()."

        except Exception as e:
            return f"Error saat Eksekusi Kode Python:\n{str(e)}"
        finally:
            sys.stdout = original_stdout
            buffer.close()
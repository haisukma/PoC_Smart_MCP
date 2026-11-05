from pathlib import Path
import pandas as pd
from io import BytesIO
from pypdf import PdfReader

def get_file_schema(file_path: str) -> str:
    """
    Mengambil ringkasan skema file (kolom, tipe data, sampel 3 baris)
    tanpa membaca seluruh isi file.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in [".csv", ".xlsx", ".xls"]:
        df = pd.read_csv(file_path) if suffix == ".csv" else pd.read_excel(file_path)
        
        buffer = []
        buffer.append(f"File: {path.name}")
        buffer.append(f"Total Baris: {len(df)}, Total Kolom: {len(df.columns)}")
        buffer.append("\nDaftar Kolom & Tipe Data:")
        for col, dtype in df.dtypes.items():
            buffer.append(f"- {col} ({dtype})")
            
        buffer.append("\nSample Data (3 baris pertama):")
        buffer.append(df.head(3).to_string(index=False))
        
        return "\n".join(buffer)

    elif suffix == ".pdf":
        try:
            text = ""

            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages[:15]):
                text += f"Halaman {i+1}\n"
                text += (page.extract_text() or "") + "\n\n"

            return text if text.strip() else "PDF berhasil dibaca, tetapi tidak ada teks yang terekstrak (mungkin berupa hasil scan/gambar)."
        except Exception as e:
            return f"Error membaca PDF: {str(e)}"
    
    raise ValueError("Format file belum didukung untuk Data Analyst Agent")
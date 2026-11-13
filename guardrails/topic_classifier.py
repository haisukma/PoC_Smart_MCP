import os
import requests
from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from dotenv import load_dotenv
from docx import Document
from io import BytesIO

load_dotenv()

API_URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "respan/span-01-lite"

def extract_file_content(file_bytes: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()

    try:
        if ext in [".csv", ".xlsx", ".xls"]:
            if ext == ".csv":
                df = pd.read_csv(BytesIO(file_bytes), nrows=10)
                return (
                    f"File type: CSV\n"
                    f"Columns: {list(df.columns)}\n"
                    f"Sample data:\n{df.to_string(index=False)}")

            excel = pd.ExcelFile(BytesIO(file_bytes))
            content = []

            for sheet in excel.sheet_names[:5]:
                df = pd.read_excel(
                    excel,
                    sheet_name=sheet,
                    nrows=10)

                content.append(
                    f"Sheet: {sheet}\n"
                    f"Columns: {list(df.columns)}\n"
                    f"Sample data:\n{df.to_string(index=False)}")

            return "\n\n".join(content)

        elif ext == ".pdf":
            reader = PdfReader(BytesIO(file_bytes))
            content = []

            for page in reader.pages[:5]:
                text = page.extract_text()
                if text:
                    content.append(text)

            return "\n".join(content)

        elif ext == ".docx":
            document = Document(BytesIO(file_bytes))

            paragraphs = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()]

            return "\n".join(paragraphs)

        else:
            raise ValueError("Format file tidak didukung")

    except Exception as e:
        raise ValueError(
            f"Gagal membaca isi file: {str(e)}")

def check_topic(user_message: str) -> float:
    api_key = os.getenv("OPEN_ROUTER_KEY")

    if not api_key:
        raise RuntimeError("OPEN_ROUTER_KEY tidak ditemukan")

    payload = {
        "model": MODEL,
        "state": user_message,
        "questions": {
            "is_on_topic": {
                "type": "noul",
                "instructions": """
                    Tugas:
                    Tentukan apakah pesan dan file yang diinputkan pengguna berkaitan dengan
                    bidang TRANSMISI TENAGA LISTRIK.

                    CAKUPAN TOPIK YANG DIIZINKAN:

                    1. ASET TRANSMISI:
                    - Item Tower transmisi listrik, seperti Arching Horn, Isolator, Spacer, dll
                    - SUTT dan SUTET
                    - Penghantar dan jalur transmisi
                    - Gardu Induk
                    - SKTT dan SKLT
                    - UPT dan ULTG
                    - Identitas jalur atau nama penghantar, termasuk nama lokasi

                    2. KEGIATAN OPERASIONAL:
                    - Inspeksi alat dan lokasi
                    - Thermovisi dan pengukuran pentanahan
                    - Pemeliharaan SKTT dan SKLT
                    - Validasi inspeksi alat, lokasi, dan menggunakan drone
                    - Assessment kondisi alat dan lokasi
                    - Identifikasi anomali
                    - Kerawanan layang-layang
                    - Proteksi petir
                    - Penjadwalan inspeksi

                    3. PENGOLAHAN DAN ANALISIS DATA:
                    - Membaca dan menganalisis file inspeksi
                    - Membuat grafik dan visualisasi data
                    - Membuat bar chart, line chart, dan pie chart
                    - Menghitung dan membandingkan kondisi aset
                    - Membuat rekapitulasi dan laporan
                    - Memfilter data berdasarkan nama jalur,tower, penghantar, lokasi, atau periode
                    - Menganalisis tren dan anomali data transmisi

                    ATURAN PENTING:

                    Permintaan pengolahan data, visualisasi, perhitungan,
                    dan pembuatan laporan tetap termasuk ON-TOPIC
                    apabila objek atau data yang dibahas berkaitan
                    dengan aset dan kegiatan transmisi tenaga listrik

                    Jangan hanya menilai berdasarkan kata kerja seperti
                    membuat grafik, menghitung, menganalisis, atau
                    membaca file. Perhatikan objek dan konteks
                    yang sedang dibahas

                    Pesan tidak harus menggunakan istilah teknis secara
                    eksplisit selama konteksnya masih berkaitan
                    dengan cakupan transmisi tenaga listrik

                    Pertanyaan dan file yang sama sekali tidak berkaitan dengan
                    cakupan tersebut termasuk OFF-TOPIC
                """,
                "criteria": {
                    "true": """
                        Pesan dan file membahas aset/item, operasional, inspeksi,
                        pemeliharaan, kondisi, atau pengolahan dan
                        analisis data yang berkaitan dengan transmisi
                        tenaga listrik
                    """,
                    "false": """
                        Pesan dan file tidak memiliki hubungan dengan aset/item,
                        operasional, kegiatan, atau data transmisi
                        tenaga listrik
                    """
                }
            }
        }
    }

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"},
        json=payload,
        timeout=30)

    if not response.ok:
        print("HTTP Status:", response.status_code)
        print("OPENROUTER ERROR:", response.text)

    response.raise_for_status()
    result = response.json()

    return float(result["answers"]["is_on_topic"]["noul"])
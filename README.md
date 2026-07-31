# Image Detection with YOLOv8n - Srintami

Proyek ini merupakan aplikasi deteksi gambar menggunakan YOLOv8n Ultralytics

## Persiapan

Pastikan Python sudah terinstall di komputer.

Cek versi Python:

```bash
python --version
```

atau

```bash
python3 --version
```

## Clone Repository

```bash
git https://github.com/haisukma/PoC_Smart_MCP.git
```

## Membuat Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

Jika berhasil, akan muncul `(venv)` di depan terminal.

## Install Dependencies

Install seluruh library yang dibutuhkan dari file `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Menjalankan API

Untuk melakukan deteksi gambar:

```bash
uvicorn main:app
```

## Menonaktifkan Virtual Environment

```bash
deactivate
```

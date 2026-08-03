from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from docx import Document
from io import BytesIO

async def extract_text(file):

    suffix = Path(file.filename).suffix.lower()
    content = await file.read()

    if suffix == ".pdf":

        reader = PdfReader(BytesIO(content))

        text = ""

        for page in reader.pages:
            text += page.extract_text() or ""

        return text

    elif suffix == ".txt":

        return content.decode("utf-8")

    elif suffix == ".csv":

        df = pd.read_csv(
            BytesIO(content),
            sep=None,
            engine="python"
        )

        return df.to_string(index=False)

    elif suffix == ".xlsx":

        df = pd.read_excel(BytesIO(content))

        return df.to_string(index=False)

    elif suffix == ".docx":

        doc = Document(BytesIO(content))

        return "\n".join(
            p.text
            for p in doc.paragraphs
        )

    raise Exception("Format file tidak didukung")
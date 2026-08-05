from pathlib import Path

def get_sales_knowledge():

    path = (
        Path(__file__).parent.parent
        / "knowledge_base"
        / "salesperformance-info.md"
    )

    return path.read_text(
        encoding="utf-8"
    )
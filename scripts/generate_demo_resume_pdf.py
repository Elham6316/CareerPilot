"""يحوّل data/demo_resume.txt إلى data/demo_resume.pdf (سيرة ذاتية تجريبية
ببيانات وهمية، للاستخدام في الاختبار والعرض بدل أي سيرة حقيقية)."""

from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

SRC = Path(__file__).parent.parent / "data" / "demo_resume.txt"
DEST = Path(__file__).parent.parent / "data" / "demo_resume.pdf"


def main() -> None:
    text = SRC.read_text(encoding="utf-8")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.split("\n"):
        if line.strip():
            pdf.multi_cell(0, 6, line, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.ln(6)
    pdf.output(str(DEST))
    print(f"تم إنشاء {DEST}")


if __name__ == "__main__":
    main()

"""استخراج نص السيرة الذاتية من ملف PDF."""

from pypdf import PdfReader


def extract_resume_text(pdf_path: str) -> str:
    """يقرأ ملف PDF ويرجع نصه الكامل. يرفع ValueError برسالة واضحة لو الملف
    غير موجود أو لا يحتوي نصاً قابلاً للاستخراج (مثلاً PDF ممسوح ضوئياً بدون OCR)."""
    reader = PdfReader(pdf_path)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages_text).strip()

    if not text:
        raise ValueError(
            "لم أستطع استخراج أي نص من هذا الملف — قد يكون PDF ممسوحاً ضوئياً "
            "بدون طبقة نص (يحتاج OCR)."
        )
    return text

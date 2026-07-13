"""عميل Gemini المشترك بين كل الأدوات في tools/."""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

# gemini-2.5-flash (المثبّت أصلاً في CLAUDE.md) لم يعد متاحاً لمفاتيح API
# الجديدة — يرجع 404 "no longer available to new users". تم التأكد بالاختبار
# الفعلي مع مفتاح المشروع، والتحويل لـ gemini-3.1-flash-lite بموافقة المستخدم.
MODEL_NAME = "models/gemini-3.1-flash-lite"

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client

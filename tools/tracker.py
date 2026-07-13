"""تسجيل ومتابعة التقديمات على الوظائف — تخزين محلي بسيط في JSON."""

import json
from datetime import date
from pathlib import Path

APPLICATIONS_FILE = Path(__file__).parent.parent / "data" / "applications.json"


def _load() -> list:
    if not APPLICATIONS_FILE.exists():
        return []
    with open(APPLICATIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(applications: list) -> None:
    APPLICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(APPLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(applications, f, ensure_ascii=False, indent=2)


def log_application(company: str, title: str, status: str) -> dict:
    """يضيف تقديماً جديداً، أو يحدّث الحالة لو كان نفس company+title مسجّلاً
    مسبقاً. يُستدعى فقط بعد تأكيد صريح من المستخدم (قرار النموذج، راجع
    SYSTEM_INSTRUCTION في agent.py)."""
    if not company or not company.strip():
        return {"error": "اسم الشركة فاضي — أعطني اسم الشركة المطلوب تسجيلها."}

    if not title or not title.strip():
        return {"error": "المسمى الوظيفي فاضي — أعطني المسمى الوظيفي المطلوب تسجيله."}

    applications = _load()
    today = date.today().isoformat()

    for app in applications:
        if (
            app["company"].strip().lower() == company.strip().lower()
            and app["title"].strip().lower() == title.strip().lower()
        ):
            app["status"] = status
            app["date"] = today
            _save(applications)
            return {"updated_existing": True, "application": app}

    new_app = {"company": company, "title": title, "status": status, "date": today}
    applications.append(new_app)
    _save(applications)
    return {"updated_existing": False, "application": new_app}


def get_application_status(filter_status: str = None) -> dict:
    """يرجع ملخصاً عن التقديمات المسجّلة: العدد الكلي، مجمّعة حسب الحالة،
    أو مفلترة حسب filter_status لو طُلب."""
    applications = _load()

    if filter_status:
        filtered = [a for a in applications if a["status"] == filter_status]
        return {"total": len(filtered), "filter_status": filter_status, "applications": filtered}

    by_status = {}
    for app in applications:
        by_status[app["status"]] = by_status.get(app["status"], 0) + 1

    return {"total": len(applications), "by_status": by_status, "applications": applications}

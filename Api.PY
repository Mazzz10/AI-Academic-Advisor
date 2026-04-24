"""
Api.PY
------
FastAPI backend - يستخدم النموذج الذكي الجديد
"""

import re
import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from course_graph import build_full_cs_graph
from model import build_full_schedule, ALL_COURSES

# ============================================================
# تحميل النموذج
# ============================================================

try:
    model       = joblib.load("model.pkl")
    all_courses = joblib.load("all_courses.pkl")
    G           = build_full_cs_graph()
    print("النموذج محمل بنجاح")
except Exception as e:
    print(f"خطأ في تحميل النموذج: {e}")
    raise

# ============================================================
# إعداد التطبيق
# ============================================================

app = FastAPI(
    title="Academic Advisor API",
    description="نظام اقتراح الجدول الدراسي بالذكاء الاصطناعي",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Pydantic Models
# ============================================================

class StudentInput(BaseModel):
    """
    grades: { "كود المادة": الدرجة }
    مثال:
    {
        "grades": {
            "إنجل 3111": 85,
            "تقا 3110": 72,
            "ريض 3111": 55
        },
        "num_semesters_done": 1
    }
    """
    grades: Dict[str, float]
    num_semesters_done: int = 1

# ============================================================
# دالة تنظيف رموز المواد
# ============================================================

def normalize_code(code: str) -> str:
    """توحيد شكل رمز المادة للمطابقة الصحيحة"""
    code = code.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    code = re.sub(r'\s+', ' ', code).strip()
    return code

def clean_grades(raw_grades: Dict[str, float]) -> Dict[str, float]:
    """
    تنظيف ومطابقة رموز المواد مع الـ graph
    يحل مشكلة الاختلاف في الهمزات والمسافات
    """
    cleaned = {}
    node_map = {normalize_code(n): n for n in G.nodes()}

    for raw_code, grade in raw_grades.items():
        normalized = normalize_code(raw_code)
        if normalized in node_map:
            original_code = node_map[normalized]
            cleaned[original_code] = grade
        # إذا لم يجد المادة يتجاهلها بدل ما يرمي error

    return cleaned

# ============================================================
# Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Academic Advisor API v2.0 - يعمل بنموذج توصية ذكي",
        "docs": "http://localhost:8000/docs"
    }


@app.get("/courses")
def get_all_courses():
    """
    إرجاع جميع المواد مع بياناتها ومتطلباتها
    يستخدمه الفرونت اند لعرض قائمة المواد
    """
    courses = []
    for code, data in G.nodes(data=True):
        courses.append({
            "code":    code,
            "name":    data["name"],
            "level":   data["level"],
            "hours":   data["hours"],
            "prereqs": list(G.predecessors(code)),
        })
    courses.sort(key=lambda x: x["level"])
    return {"total": len(courses), "courses": courses}


@app.post("/suggest")
def suggest_schedule(student: StudentInput):
    """
    الـ endpoint الرئيسي:
    - يستقبل درجات الطالب
    - النموذج يحلل أداءه في كل مادة
    - يوصي بالجدول الأنسب له فصلاً بعد فصل حتى التخرج
    - كل مادة مقترحة تأتي مع نسبة ثقة النموذج بها
    """
    if not student.grades:
        raise HTTPException(
            status_code=400,
            detail="يجب إدخال درجات مادة واحدة على الأقل"
        )

    # تنظيف الرموز ومطابقتها
    cleaned_grades = clean_grades(student.grades)

    if not cleaned_grades:
        raise HTTPException(
            status_code=400,
            detail="لم يتم التعرف على أي مادة. تأكد من صحة رموز المواد"
        )

    # بناء الجدول بالنموذج الذكي
    result = build_full_schedule(
        grades = cleaned_grades,
        model  = model,
        G      = G,
    )

    return result


@app.get("/student/analyze")
def analyze_student(grades_str: str):
    """
    endpoint مساعد لتحليل أداء الطالب بدون جدول
    grades_str مثال: "عال 3271:85,عال 3221:72,ريض 3111:55"
    """
    try:
        raw_grades = {}
        for pair in grades_str.split(","):
            code, grade = pair.strip().rsplit(":", 1)
            raw_grades[code.strip()] = float(grade.strip())
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="صيغة غير صحيحة. المثال الصحيح: عال 3271:85,ريض 3111:72"
        )

    cleaned = clean_grades(raw_grades)
    if not cleaned:
        raise HTTPException(status_code=400, detail="لم يتم التعرف على أي مادة")

    passed     = {c: g for c, g in cleaned.items() if g >= 60}
    failed     = {c: g for c, g in cleaned.items() if g < 60}
    passed_vals = list(passed.values())

    gpa       = round(float(np.mean(passed_vals)), 2) if passed_vals else 0.0
    fail_rate = round(len(failed) / len(cleaned) * 100, 1) if cleaned else 0.0

    # تحليل الأداء حسب المستوى
    level_analysis = {}
    for level in range(1, 11):
        level_courses = {
            c: g for c, g in passed.items()
            if c in G.nodes and G.nodes[c]["level"] == level
        }
        if level_courses:
            level_analysis[f"مستوى {level}"] = round(float(np.mean(list(level_courses.values()))), 2)

    # نقاط الضعف (مواد رسب فيها)
    weak_points = [
        {"code": c, "name": G.nodes[c]["name"], "grade": g}
        for c, g in failed.items()
        if c in G.nodes
    ]

    return {
        "gpa":            gpa,
        "fail_rate":      f"{fail_rate}%",
        "passed_count":   len(passed),
        "failed_count":   len(failed),
        "level_analysis": level_analysis,
        "weak_points":    weak_points,
    }


# ============================================================
# تشغيل السيرفر
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Api:app", host="127.0.0.1", port=8000, reload=True)
"""
api.py
------
FastAPI backend - نظام اقتراح الجدول الدراسي بالذكاء الاصطناعي
"""

import sys
import io
import re
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
from course_graph import build_full_cs_graph

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 1. المقياس المئوي (لنموذج الذكاء الاصطناعي)
GRADE_PERCENTAGES = {
    "A+": 98.0, "A": 95.0, "B+": 88.0, "B": 85.0,
    "C+": 78.0, "C": 75.0, "D+": 68.0, "D": 65.0, "F": 50.0
}

# 2. المقياس الجامعي (للعرض في واجهة المستخدم)
GRADE_POINTS_5 = {
    "A+": 5.00, "A": 4.75, "B+": 4.50, "B": 4.00,
    "C+": 3.50, "C": 3.00, "D+": 2.50, "D": 2.00, "F": 1.00
}

# ============================================================
# تحميل النموذج
# ============================================================
try:
    model        = joblib.load("model.pkl")
    le           = joblib.load("label_encoder.pkl")
    feature_cols = joblib.load("feature_cols.pkl")
    G            = build_full_cs_graph()
except Exception as e:
    print(f" خطأ في التحميل: {e}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StudentInput(BaseModel):
    grades: Dict[str, float]
    num_semesters_done: int

# ============================================================
# دوال التنظيف والتحليل المعالجة للمشاكل
# ============================================================

def normalize_code(code):
    """توحيد شكل الرمز: إزالة المسافات الزائدة وتوحيد شكل الألف والهمزات"""
    code = code.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    code = re.sub(r'\s+', ' ', code).strip()
    return code

def parse_grade(g):
    """دالة ذكية لتحويل الدرجات سواء كانت حروف، نسب مئوية، أو من 5"""
    g_str = str(g).upper().strip()
    
    if g_str in GRADE_PERCENTAGES:
        return GRADE_PERCENTAGES[g_str], GRADE_POINTS_5[g_str]
        
    try:
        num = float(g)
        if num <= 5.0:
            return (num / 5.0) * 100, num
        else:
            if num >= 95: pts = 5.00
            elif num >= 90: pts = 4.75
            elif num >= 85: pts = 4.50
            elif num >= 80: pts = 4.00
            elif num >= 75: pts = 3.50
            elif num >= 70: pts = 3.00
            elif num >= 65: pts = 2.50
            elif num >= 60: pts = 2.00
            else: pts = 1.00
            return num, pts
    except:
        return 60.0, 0.0

def build_student_features(grades, num_semesters_done):
    """نبني المميزات بالضبط كما تدرب عليها الـ Random Forest في model.py"""
    
    # تحويل جميع الدرجات لنسبة مئوية من أجل الذكاء الاصطناعي
    parsed_grades = {code: parse_grade(g)[0] for code, g in grades.items()}
    passed = {code: score for code, score in parsed_grades.items() if score >= 60}
    all_scores = list(parsed_grades.values())

    gpa = np.mean(list(passed.values())) if passed else 0.0
    fail_rate = sum(1 for score in all_scores if score < 60) / len(all_scores) if all_scores else 0.0
    completed_count = len(passed)
    avg_hours = 15.0

    # حساب معدل كل مستوى لكي يفهم المودل أن الطالب متفوق!
    level_grades = {}
    for level in range(1, 11):
        level_courses_scores = []
        for c, score in passed.items():
            matches = re.findall(r'([ا-يأإآa-zA-Z]{3,4}\s*\d{3,4})', c)
            for m in matches:
                clean_c = normalize_code(m)
                for node in G.nodes():
                    if normalize_code(node) == clean_c:
                        if G.nodes[node].get("level") == level:
                            level_courses_scores.append(score)
                        break
        level_grades[f"gpa_level_{level}"] = np.mean(level_courses_scores) if level_courses_scores else 0.0

    # تجهيز مصفوفة البيانات النهائية
    data = {col: 0.0 for col in feature_cols}
    if "gpa" in data: data["gpa"] = gpa
    if "GPA" in data: data["GPA"] = gpa
    if "fail_rate" in data: data["fail_rate"] = fail_rate
    if "completed_count" in data: data["completed_count"] = completed_count
    if "num_semesters" in data: data["num_semesters"] = num_semesters_done
    if "avg_hours" in data: data["avg_hours"] = avg_hours

    for k, v in level_grades.items():
        if k in data:
            data[k] = v

    return pd.DataFrame([data])[feature_cols]

def build_schedule(grades, model, le, feature_cols, num_semesters_done):
    X = build_student_features(grades, num_semesters_done)
    profile_encoded = model.predict(X)[0]
    profile_name = le.inverse_transform([profile_encoded])[0]
    
    # --- حدود الساعات الديناميكية ---
    if profile_name == "متفوق":
        max_hours = 20
    elif profile_name == "جيد":
        max_hours = 17
    else: # متوسط أو ضعيف
        max_hours = 15 

    # 1. مطابقة المواد
    completed_original = set()
    for raw_code in grades.keys():
        matches = re.findall(r'([ا-يأإآa-zA-Z]{3,4}\s*\d{3,4})', raw_code)
        for m in matches:
            clean_input = normalize_code(m)
            for node in G.nodes():
                if normalize_code(node) == clean_input:
                    completed_original.add(node)
                    break

                # --- إخفاء المواد غير المرغوبة نهائياً ---
    # نضع المواد هنا ليقوم النظام بتجاهلها تماماً واعتبارها مجتازة
    courses_to_hide = ["مهج 3111", "مهج 3110"] 
    for node in G.nodes():
        if normalize_code(node) in [normalize_code(c) for c in courses_to_hide]:
            completed_original.add(node)
    # ----------------------------------------
    
    # 2. المواد المتبقية
    remaining = set([n for n in G.nodes() if n not in completed_original])
    
    # 2. المواد المتبقية
    remaining = set([n for n in G.nodes() if n not in completed_original])
    schedule = []
    current_sem = num_semesters_done + 1
    
    # 3. بناء الجدول (Knapsack)
    while remaining:
        current_level_courses = []
        current_hours = 0
        courses_to_remove = []
        
        for course in list(remaining):
            course_info = G.nodes[course]
            preds = list(G.predecessors(course))
            
            if all(p in completed_original for p in preds):
                c_hours = course_info['hours']
                if current_hours + c_hours <= max_hours:
                    current_level_courses.append({
                        "code": course,
                        "name": course_info['name'],
                        "hours": c_hours
                    })
                    current_hours += c_hours
                    courses_to_remove.append(course)

                if current_hours >= max_hours:
                    break
        
        if not current_level_courses:
            break
            
        for c in courses_to_remove:
            completed_original.add(c)
            remaining.remove(c)
            
        schedule.append({
            "semester": current_sem,
            "total_hours": current_hours,
            "courses": current_level_courses
        })
        current_sem += 1
    
    # 4. حساب المعدل التراكمي للعرض (من 5.0)
    numeric_grades_5 = [parse_grade(g)[1] for g in grades.values()]
    display_gpa = round(float(np.mean(numeric_grades_5)), 2) if numeric_grades_5 else 0.0

    return {
        "predicted_profile": profile_name,
        "gpa": display_gpa,
        "remaining_semesters": len(schedule),
        "schedule": schedule
    }

@app.post("/suggest")
def suggest_endpoint(student: StudentInput):
    result = build_schedule(
        grades             = student.grades,
        model              = model,
        le                 = le,
        feature_cols       = feature_cols,
        num_semesters_done = student.num_semesters_done,
    )
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
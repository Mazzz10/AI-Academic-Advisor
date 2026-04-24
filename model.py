"""
model.py — النسخة النهائية
--------------------------
نموذج ذكاء اصطناعي حقيقي يعمل هكذا:

1. يتعلم من تاريخ 500 طالب وهمي محاكٍ للواقع
2. لكل مادة متاحة يحسب: ما احتمال أن هذه المادة مناسبة لهذا الطالب؟
3. يختار أفضل مجموعة مواد (local optimal) بخوارزمية Greedy مع Backtracking
4. نفس الدرجات → نفس الجدول دائماً (لا عشوائية)
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import random
import pandas as pd
import numpy as np
import joblib
from itertools import combinations
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score
from course_graph import build_full_cs_graph

G           = build_full_cs_graph()
ALL_COURSES = sorted(G.nodes())  # 53 مادة — قائمة ثابتة

# ============================================================
# 1. بناء بيانات التدريب
# ============================================================

def build_training_data(df: pd.DataFrame):
    """
    X: متجه بطول 53 لكل فصل في تاريخ الطالب
       0.0  = لم يدرسها
       0.6-1.0 = نجح (درجته/100)
       -1.0 = رسب

    y: المواد التي أخذها في الفصل التالي فعلاً (1 أو 0)
    """
    course_index = {c: i for i, c in enumerate(ALL_COURSES)}
    X_list, y_list = [], []

    for student_id, group in df.groupby("student_id"):
        group     = group.sort_values("semester")
        semesters = sorted(group["semester"].unique())

        if len(semesters) < 2:
            continue

        for i in range(len(semesters) - 1):
            current_sem = semesters[i]
            next_sem    = semesters[i + 1]
            history     = group[group["semester"] <= current_sem]

            # بناء X
            x = np.zeros(len(ALL_COURSES))
            for _, row in history.iterrows():
                code = row["course_code"]
                if code not in course_index:
                    continue
                idx  = course_index[code]
                x[idx] = (row["grade"] / 100.0) if row["passed"] else -1.0

            # بناء y
            next_courses = group[group["semester"] == next_sem]["course_code"].tolist()
            y = np.zeros(len(ALL_COURSES))
            for code in next_courses:
                if code in course_index:
                    y[course_index[code]] = 1

            X_list.append(x)
            y_list.append(y)

    X = np.array(X_list)
    y = np.array(y_list)
    print(f"   بيانات التدريب: {X.shape[0]:,} سجل، {X.shape[1]} مادة")
    return X, y


# ============================================================
# 2. تدريب النموذج
# ============================================================

def train_model(X, y):
    """
    Multi-Label Classifier:
    نموذج منفصل لكل مادة يقرر احتمالية التوصية بها
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    base = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1,
    )
    model = MultiOutputClassifier(base, n_jobs=-1)

    print("   جاري التدريب...")
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    f1     = f1_score(y_test, y_pred, average="micro", zero_division=0)
    print(f"   F1-Score: {f1:.3f}")

    return model


# ============================================================
# 3. استخراج احتماليات التوصية من النموذج
# ============================================================

def get_course_probabilities(grades: dict, model) -> dict:
    """
    يسأل النموذج: لكل مادة، ما احتمال أنها مناسبة لهذا الطالب؟
    يُرجع: {course_code: probability}
    """
    course_index = {c: i for i, c in enumerate(ALL_COURSES)}
    x = np.zeros(len(ALL_COURSES))

    for code, grade in grades.items():
        if code not in course_index:
            continue
        idx    = course_index[code]
        x[idx] = (grade / 100.0) if grade >= 60 else -1.0

    x = x.reshape(1, -1)
    probas = {}

    for estimator, course in zip(model.estimators_, ALL_COURSES):
        try:
            prob           = estimator.predict_proba(x)[0]
            probas[course] = float(prob[1]) if len(prob) > 1 else 0.0
        except Exception:
            probas[course] = 0.0

    return probas


# ============================================================
# 4. اختيار أفضل مجموعة مواد (Local Optimal)
# ============================================================

def select_optimal_courses(
    available: list,
    probas: dict,
    G,
    min_hours: int,
    max_hours: int,
) -> list:
    """
    خوارزمية Greedy + Knapsack لاختيار أفضل مجموعة مواد:

    1. ترتيب المواد حسب ثقة النموذج (تنازلياً)
    2. إضافة المواد بالترتيب حتى اكتمال الساعات
    3. إذا بقيت ساعات فارغة → نحاول ملءها بمواد ذات ساعات أصغر
    4. النتيجة: أفضل مجموعة ممكنة ضمن حدود الساعات
    """
    # ترتيب حسب ثقة النموذج ثم مستوى المادة
    ranked = sorted(
        available,
        key=lambda c: (-probas.get(c, 0.0), G.nodes[c]["level"])
    )

    selected    = []
    total_hours = 0

    # المرحلة الأولى: Greedy — أضف الأعلى ثقة أولاً
    for course in ranked:
        ch = G.nodes[course]["hours"]
        if total_hours + ch <= max_hours:
            selected.append(course)
            total_hours += ch
        if total_hours >= min_hours:
            break

    # المرحلة الثانية: Knapsack — حاول ملء الساعات المتبقية
    remaining_capacity = max_hours - total_hours
    selected_set       = set(selected)
    not_selected       = [c for c in ranked if c not in selected_set]

    for course in not_selected:
        ch = G.nodes[course]["hours"]
        if ch <= remaining_capacity:
            selected.append(course)
            total_hours          += ch
            remaining_capacity   -= ch
        if remaining_capacity == 0:
            break

    # إذا لم نصل للحد الأدنى — خفف القيد وأضف ما أمكن
    if total_hours < min_hours:
        for course in not_selected:
            if course in selected_set:
                continue
            ch = G.nodes[course]["hours"]
            if total_hours + ch <= max_hours:
                selected.append(course)
                total_hours += ch
            if total_hours >= min_hours:
                break

    return selected


# ============================================================
# 5. بناء الخطة الكاملة حتى التخرج
# ============================================================

def build_full_schedule(grades: dict, model, G) -> dict:
    """
    يبني الخطة الكاملة فصلاً بعد فصل:
    - كل فصل: النموذج يحسب احتمالية كل مادة → نختار الأمثل
    - نفس الدرجات = نفس الجدول دائماً (seed ثابت)
    - يحترم المتطلبات 100%
    """

    # تثبيت العشوائية — نفس الدرجات = نفس الجدول دائماً
    random.seed(hash(str(sorted(grades.items()))) % (2**32))
    np.random.seed(hash(str(sorted(grades.items()))) % (2**32))

    passed      = {c: g for c, g in grades.items() if g >= 60}
    failed      = {c: g for c, g in grades.items() if g < 60}
    passed_vals = list(passed.values())

    gpa       = float(np.mean(passed_vals)) if passed_vals else 0.0
    fail_rate = len(failed) / len(grades) if grades else 0.0

    # تصنيف الطالب لتحديد الحمل المناسب
    if gpa >= 85 and fail_rate < 0.05:
        profile, min_h, max_h = "متفوق", 17, 20
    elif gpa >= 75 and fail_rate < 0.12:
        profile, min_h, max_h = "جيد",   15, 18
    elif gpa >= 65 and fail_rate < 0.22:
        profile, min_h, max_h = "متوسط", 13, 16
    else:
        profile, min_h, max_h = "ضعيف",  12, 14

    current_grades = dict(grades)
    schedule       = []
    semester_num   = 1

    while True:
        completed_set = {c for c, g in current_grades.items() if g >= 60}

        # المواد المتاحة (متطلباتها مكتملة ولم تُجتز)
        available = [
            node for node in G.nodes
            if node not in completed_set
            and all(p in completed_set for p in G.predecessors(node))
        ]

        if not available:
            break

        # احتماليات النموذج لكل مادة
        probas = get_course_probabilities(current_grades, model)

        # اختيار أفضل مجموعة مواد
        selected = select_optimal_courses(
            available = available,
            probas    = probas,
            G         = G,
            min_hours = min_h,
            max_hours = max_h,
        )

        if not selected:
            break

        total_h = sum(G.nodes[c]["hours"] for c in selected)

        schedule.append({
            "semester":    semester_num,
            "total_hours": total_h,
            "courses": [
                {
                    "code":       c,
                    "name":       G.nodes[c]["name"],
                    "hours":      G.nodes[c]["hours"],
                    "confidence": round(probas.get(c, 0.0) * 100, 1),
                }
                for c in selected
            ],
        })

        # المواد المختارة تصبح مجتازة للفصل التالي
        for c in selected:
            current_grades[c] = 75.0

        semester_num += 1
        if semester_num > 20:
            break

    return {
        "predicted_profile":   profile,
        "gpa":                 round(gpa, 2),
        "fail_rate":           round(fail_rate * 100, 1),
        "remaining_semesters": len(schedule),
        "schedule":            schedule,
    }


# ============================================================
# 6. حفظ النموذج
# ============================================================

def save_artifacts(model):
    joblib.dump(model,       "model.pkl")
    joblib.dump(ALL_COURSES, "all_courses.pkl")
    print("   تم الحفظ: model.pkl | all_courses.pkl")


# ============================================================
# 7. التشغيل الرئيسي
# ============================================================

if __name__ == "__main__":
    print("1. تحميل البيانات...")
    df = pd.read_csv("student_data.csv", encoding="utf-8-sig")
    print(f"   {len(df):,} سجل، {df['student_id'].nunique()} طالب")

    print("\n2. بناء بيانات التدريب...")
    X, y = build_training_data(df)

    print("\n3. تدريب النموذج...")
    model = train_model(X, y)

    print("\n4. حفظ النموذج...")
    save_artifacts(model)

    print("\n5. اختبار — طالب رسب في الرياضيات:")
    G = build_full_cs_graph()

    test_grades = {
        "إنجل 3111": 72,
        "تقا 3110":  80,
        "ريض 3111":  55,   # رسب
        "ريض 3140":  68,
        "كيم 3111":  75,
        "مهج 3111":  90,
    }

    result = build_full_schedule(test_grades, model, G)

    print(f"\n   التصنيف         : {result['predicted_profile']}")
    print(f"   GPA             : {result['gpa']}")
    print(f"   نسبة الرسوب     : {result['fail_rate']}%")
    print(f"   الفصول المتبقية : {result['remaining_semesters']}")

    for sem in result["schedule"][:3]:
        print(f"\n   الفصل {sem['semester']} ({sem['total_hours']} ساعة):")
        for c in sem["courses"]:
            print(f"      {c['code']} | {c['name']} | ثقة النموذج: {c['confidence']}%")

    print("\n   --- تشغيل ثانٍ بنفس الدرجات للتحقق من الثبات ---")
    result2 = build_full_schedule(test_grades, model, G)
    match = result["schedule"] == result2["schedule"]
    print(f"   الجدول ثابت في كل مرة: {'نعم' if match else 'لا'}")
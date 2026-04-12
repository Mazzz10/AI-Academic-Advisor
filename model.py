"""
model.py
--------
يقوم هذا الملف بـ:
1. تحميل بيانات الطلاب من student_data.csv
2. استخراج الـ features لكل طالب
3. تدريب نموذج Random Forest لتصنيف الطالب
4. بناء دالة اقتراح الجدول الدراسي بناءً على التصنيف
5. حفظ النموذج للاستخدام لاحقاً في الـ API
"""

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.preprocessing import LabelEncoder
from course_graph import build_full_cs_graph

# ============================================================
# 1. تحميل البيانات
# ============================================================

def load_data(path: str = "student_data.csv") -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    print(f"  تم تحميل البيانات: {len(df):,} سجل، {df['student_id'].nunique()} طالب")
    return df


# ============================================================
# 2. استخراج الـ Features لكل طالب
# ============================================================

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    لكل طالب نستخرج:
    - GPA الكلي
    - نسبة الرسوب
    - عدد المواد المكتملة
    - متوسط درجات كل مستوى (1 إلى 10)
    - عدد الفصول المستغرقة
    - متوسط الساعات المأخوذة في كل فصل
    """
    features_list = []

    for student_id, group in df.groupby("student_id"):
        passed = group[group["passed"] == True]
        failed = group[group["passed"] == False]

        gpa              = passed["grade"].mean() if len(passed) > 0 else 0.0
        fail_rate        = len(failed) / len(group)
        completed_count  = len(passed)
        num_semesters    = group["semester"].nunique()
        avg_hours        = group.groupby("semester")["course_hours"].sum().mean()
        profile          = group["profile"].iloc[0]

        # متوسط درجات كل مستوى
        level_grades = {}
        for level in range(1, 11):
            level_passed = passed[passed["course_level"] == level]
            level_grades[f"gpa_level_{level}"] = (
                level_passed["grade"].mean() if len(level_passed) > 0 else 0.0
            )

        record = {
            "student_id":       student_id,
            "gpa":              round(gpa, 2),
            "fail_rate":        round(fail_rate, 3),
            "completed_count":  completed_count,
            "num_semesters":    num_semesters,
            "avg_hours":        round(avg_hours, 2),
            "profile":          profile,   # هذا هو الـ target
        }
        record.update(level_grades)
        features_list.append(record)

    features_df = pd.DataFrame(features_list)
    print(f"  تم استخراج الـ features: {features_df.shape[1] - 2} خاصية لكل طالب")
    return features_df


# ============================================================
# 3. تدريب النموذج
# ============================================================

def train_model(features_df: pd.DataFrame):
    """
    نموذج Random Forest لتصنيف الطالب إلى:
    متفوق / جيد / متوسط / ضعيف
    """
    feature_cols = [c for c in features_df.columns if c not in ["student_id", "profile"]]
    X = features_df[feature_cols]
    y = features_df["profile"]

    # ترميز الـ target
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    # تقييم النموذج
    y_pred = model.predict(X_test)
    print("\n  تقرير الأداء:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    return model, le, feature_cols


# ============================================================
# 4. دالة اقتراح الجدول الدراسي
# ============================================================

def suggest_schedule(
    completed_courses: list[str],
    grades: dict[str, float],
    model,
    le: LabelEncoder,
    feature_cols: list[str],
    G,
    num_semesters_done: int = 1,
) -> list[dict]:
    """
    بناءً على:
    - completed_courses : قائمة رموز المواد التي أكملها الطالب
    - grades            : {course_code: grade}
    - النموذج المدرب

    تُرجع:
    - قائمة فصول مقترحة حتى التخرج
    """

    # --- بناء features للطالب الحالي ---
    passed = {c: g for c, g in grades.items() if g >= 60}
    gpa         = np.mean(list(passed.values())) if passed else 0.0
    all_grades  = list(grades.values())
    fail_rate   = sum(1 for g in all_grades if g < 60) / len(all_grades) if all_grades else 0.0
    completed_count = len(passed)
    avg_hours   = 15.0  # افتراضي إذا لم نعرف

    level_grades = {}
    for level in range(1, 11):
        level_courses = [
            g for c, g in passed.items()
            if c in G.nodes and G.nodes[c]["level"] == level
        ]
        level_grades[f"gpa_level_{level}"] = np.mean(level_courses) if level_courses else 0.0

    student_features = { 
        "gpa":              gpa,
        "fail_rate":        fail_rate,
        "completed_count":  completed_count,
        "num_semesters":    num_semesters_done,
        "avg_hours":        avg_hours,
    }
    student_features.update(level_grades)

    X_student = pd.DataFrame([student_features])[feature_cols]

    # --- تصنيف الطالب ---
    profile_encoded = model.predict(X_student)[0]
    profile_name    = le.inverse_transform([profile_encoded])[0]

    # --- تحديد هدف الساعات بناءً على التصنيف ---
    hours_targets = {
        "متفوق": (17, 20),
        "جيد":   (15, 18),
        "متوسط": (13, 16),
        "ضعيف":  (12, 14),
    }
    min_h, max_h = hours_targets.get(profile_name, (12, 18))

    # --- اقتراح الفصول ---
    completed_set = set(passed.keys())
    schedule      = []
    semester_num  = num_semesters_done + 1

    while True:
        # المواد المتاحة
        available = []
        for node in G.nodes:
            if node in completed_set:
                continue
            prereqs = list(G.predecessors(node))
            if all(p in completed_set for p in prereqs):
                available.append(node)

        if not available:
            break  # الطالب أنهى جميع المواد

        # اختيار المواد للفصل
        available_sorted = sorted(available, key=lambda c: G.nodes[c]["level"])
        selected   = []
        total_h    = 0
        target_h   = random.randint(min_h, max_h) if profile_name != "ضعيف" else min_h

        import random
        for course in available_sorted:
            ch = G.nodes[course]["hours"]
            if total_h + ch > 20:
                continue
            selected.append(course)
            total_h += ch
            if total_h >= target_h:
                break

        if not selected:
            break

        schedule.append({
            "semester":      semester_num,
            "courses":       [
                {
                    "code":  c,
                    "name":  G.nodes[c]["name"],
                    "hours": G.nodes[c]["hours"],
                }
                for c in selected
            ],
            "total_hours":   total_h,
        })

        # نفترض أن الطالب سيكمل هذه المواد للمضي في الاقتراح
        completed_set.update(selected)
        semester_num += 1

    return {
        "predicted_profile": profile_name,
        "remaining_semesters": len(schedule),
        "schedule": schedule,
    }


# ============================================================
# 5. الحفظ والتشغيل
# ============================================================

def save_artifacts(model, le, feature_cols):
    joblib.dump(model,        "model.pkl")
    joblib.dump(le,           "label_encoder.pkl")
    joblib.dump(feature_cols, "feature_cols.pkl")
    print("\n  تم الحفظ: model.pkl | label_encoder.pkl | feature_cols.pkl")


if __name__ == "__main__":
    import random

    # 1. تحميل البيانات
    df = load_data("student_data.csv")

    # 2. استخراج الـ features
    features_df = extract_features(df)

    # 3. تدريب النموذج
    model, le, feature_cols = train_model(features_df)

    # 4. حفظ كل شيء
    save_artifacts(model, le, feature_cols)

    # 5. مثال على اقتراح جدول لطالب وهمي
    G = build_full_cs_graph()

    example_completed = ["إنجل 3111", "تقا 3110", "ريض 3111", "ريض 3140", "كيم 3111", "مهج 3111"]
    example_grades    = {c: random.uniform(65, 95) for c in example_completed}

    print("\n🎓 مثال — اقتراح جدول لطالب أكمل المستوى الأول:")
    result = suggest_schedule(
        completed_courses = example_completed,
        grades            = example_grades,
        model             = model,
        le                = le,
        feature_cols      = feature_cols,
        G                 = G,
        num_semesters_done= 1,
    )

    print(f"   التصنيف المتوقع  : {result['predicted_profile']}")
    print(f"   الفصول المتبقية  : {result['remaining_semesters']}")
    for sem in result["schedule"][:3]:   # نطبع أول 3 فصول فقط
        print(f"\n   الفصل {sem['semester']} ({sem['total_hours']} ساعة):")
        for course in sem["courses"]:
            print(f"      - {course['code']} | {course['name']} | {course['hours']} ساعات")
    print("\n   ... (بقية الفصول ستظهر في الـ API)")
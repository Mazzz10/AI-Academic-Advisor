import random
import pandas as pd
from faker import Faker
from course_graph import build_full_cs_graph

fake = Faker("ar_SA")
random.seed(42)

# ============================================================
# إعدادات عامة
# ============================================================
NUM_STUDENTS = 500          # عدد الطلاب الوهميين
MIN_HOURS = 12              # الحد الأدنى للساعات في الفصل
MAX_HOURS = 20              # الحد الأقصى للساعات في الفصل
MAX_SEMESTERS = 14          # أقصى عدد فصول قبل التوقف

# ============================================================
# أنواع الطلاب (تؤثر على الأداء العام)
# ============================================================
STUDENT_PROFILES = {
    "متفوق":    {"weight": 0.20, "grade_mu": 88, "grade_sigma": 6,  "fail_prob": 0.03},
    "جيد":      {"weight": 0.40, "grade_mu": 76, "grade_sigma": 8,  "fail_prob": 0.08},
    "متوسط":    {"weight": 0.25, "grade_mu": 65, "grade_sigma": 10, "fail_prob": 0.15},
    "ضعيف":     {"weight": 0.15, "grade_mu": 54, "grade_sigma": 12, "fail_prob": 0.28},
}

# ============================================================
# دوال مساعدة
# ============================================================

def pick_profile() -> tuple[str, dict]:
    """اختيار نوع الطالب عشوائياً حسب الأوزان."""
    profiles = list(STUDENT_PROFILES.items())
    weights  = [p["weight"] for _, p in profiles]
    name, profile = random.choices(profiles, weights=weights, k=1)[0]
    return name, profile


def generate_grade(profile: dict, passed: bool) -> float:
    """
    توليد درجة واقعية.
    - إذا رسب: درجة بين 40 و 59
    - إذا نجح: درجة بين 60 و 100 مع توزيع غاوسي حسب نوع الطالب
    """
    if not passed:
        return round(random.uniform(40, 59), 1)
    grade = random.gauss(profile["grade_mu"], profile["grade_sigma"])
    return round(max(60.0, min(100.0, grade)), 1)


def get_available_courses(G, completed: set) -> list:
    """
    إرجاع المواد التي يمكن للطالب أخذها الآن:
    - جميع متطلباتها السابقة مكتملة بنجاح
    - لم يأخذها بعد
    """
    available = []
    for node in G.nodes:
        if node in completed:
            continue
        prereqs = list(G.predecessors(node))
        if all(p in completed for p in prereqs):
            available.append(node)
    return available


def select_semester_courses(G, available: list, completed: set, profile: dict) -> list:
    """
    اختيار مجموعة مواد للفصل بحيث:
    - مجموع الساعات بين MIN_HOURS و MAX_HOURS
    - الطالب الجيد يفضل أخذ أكثر، والضعيف يأخذ أقل
    """
    # ترتيب المواد حسب المستوى ثم عشوائياً لمحاكاة اختيارات الطالب
    available_sorted = sorted(available, key=lambda c: (G.nodes[c]["level"], random.random()))

    # تحديد هدف الساعات حسب نوع الطالب
    if profile["fail_prob"] < 0.1:       # متفوق وجيد
        target_hours = random.randint(16, MAX_HOURS)
    elif profile["fail_prob"] < 0.2:     # متوسط
        target_hours = random.randint(14, 18)
    else:                                # ضعيف
        target_hours = random.randint(MIN_HOURS, 16)

    selected = []
    total_hours = 0

    for course in available_sorted:
        course_hours = G.nodes[course]["hours"]
        if total_hours + course_hours > MAX_HOURS:
            continue
        selected.append(course)
        total_hours += course_hours
        if total_hours >= target_hours:
            break

    # ضمان الحد الأدنى للساعات — إذا لم نصل لـ 12 نضيف ما أمكن
    if total_hours < MIN_HOURS:
        for course in available_sorted:
            if course in selected:
                continue
            course_hours = G.nodes[course]["hours"]
            if total_hours + course_hours <= MAX_HOURS:
                selected.append(course)
                total_hours += course_hours
            if total_hours >= MIN_HOURS:
                break

    return selected


# ============================================================
# المولّد الرئيسي
# ============================================================

def simulate_student(student_id: int, G) -> list[dict]:
    """
    محاكاة المسار الدراسي الكامل لطالب واحد.
    تُرجع قائمة من السجلات (كل سجل = مادة في فصل).
    """
    profile_name, profile = pick_profile()
    records = []

    completed   = set()   # المواد التي اجتازها الطالب بنجاح
    failed_once = set()   # المواد التي رسب فيها مرة (لرفع احتمال النجاح لاحقاً)
    semester    = 1

    while semester <= MAX_SEMESTERS:
        available = get_available_courses(G, completed)

        # إذا لم تعد هناك مواد متاحة → الطالب أنهى الخطة
        if not available:
            break

        selected = select_semester_courses(G, available, completed, profile)

        # إذا لم نتمكن من اختيار أي مادة (حالة نادرة)
        if not selected:
            break

        for course in selected:
            # إذا رسب الطالب في هذه المادة سابقاً، احتمال النجاح يرتفع
            adjusted_fail_prob = profile["fail_prob"] * 0.5 if course in failed_once else profile["fail_prob"]
            passed = random.random() > adjusted_fail_prob
            grade  = generate_grade(profile, passed)

            records.append({
                "student_id":    student_id,
                "profile":       profile_name,
                "semester":      semester,
                "course_code":   course,
                "course_name":   G.nodes[course]["name"],
                "course_level":  G.nodes[course]["level"],
                "course_hours":  G.nodes[course]["hours"],
                "grade":         grade,
                "passed":        passed,
            })

            if passed:
                completed.add(course)
            else:
                failed_once.add(course)

        semester += 1

    return records


# ============================================================
# التشغيل الرئيسي
# ============================================================

def generate_dataset(num_students: int = NUM_STUDENTS) -> pd.DataFrame:
    G = build_full_cs_graph()
    all_records = []

    for i in range(1, num_students + 1):
        student_records = simulate_student(student_id=i, G=G)
        all_records.extend(student_records)

    df = pd.DataFrame(all_records)
    return df


if __name__ == "__main__":
    print("  جاري توليد البيانات...")
    df = generate_dataset()

    # حفظ البيانات
    df.to_csv("student_data.csv", index=False, encoding="utf-8-sig")

    # إحصائيات سريعة للتحقق
    print(f"\n   تم توليد البيانات بنجاح!")
    print(f"   إجمالي السجلات  : {len(df):,}")
    print(f"   عدد الطلاب      : {df['student_id'].nunique()}")
    print(f"   متوسط الدرجات   : {df['grade'].mean():.1f}")
    print(f"   نسبة الرسوب     : {(~df['passed']).mean() * 100:.1f}%")
    print(f"\n   توزيع أنواع الطلاب:")
    profile_dist = df.drop_duplicates("student_id")["profile"].value_counts()
    for profile, count in profile_dist.items():
        print(f"   - {profile}: {count} طالب")
    print(f"\n  تم الحفظ في: student_data.csv")
import React, { useState } from 'react';
import {
  User, Lock, Upload, ChevronRight, GraduationCap,
  FileText, BarChart3, Users, LogOut, CheckCircle2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import courseDictionary from './plan.json';
import html2pdf from 'html2pdf.js';

// --- المكونات الفرعية ---

const LoginPage = ({ onLogin }) => {
  const [name, setName] = useState(''); // <-- 1. New state for the student's name
  const [id, setId] = useState('');
  const [pass, setPass] = useState('');

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-md border border-slate-100"
      >
        <div className="text-center mb-8">
          <div className="bg-blue-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-200">
            <GraduationCap className="text-white w-10 h-10" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">نظام المرشد الذكي</h1>
          <p className="text-slate-500 text-sm mt-2">الجامعة الإسلامية - كلية علوم الحاسب</p>
        </div>

        <div className="space-y-4">
          {/* <-- 2. New Input Field for Name --> */}
          <div className="relative">
            <User className="absolute left-3 top-3 text-slate-400 w-5 h-5" />
            <input
              type="text" placeholder="الاسم"
              className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all"
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div className="relative">
            <FileText className="absolute left-3 top-3 text-slate-400 w-5 h-5" />
            <input
              type="text" placeholder="الرقم الجامعي"
              className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all"
              onChange={(e) => setId(e.target.value)}
            />
          </div>
          <div className="relative">
            <Lock className="absolute left-3 top-3 text-slate-400 w-5 h-5" />
            <input
              type="password" placeholder="كلمة المرور"
              className="w-full pl-10 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition-all"
              onChange={(e) => setPass(e.target.value)}
            />
          </div>
          <button
            onClick={() => onLogin(id, pass, name)} // <-- 3. Pass the name to the onLogin function
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-blue-100 flex items-center justify-center gap-2"
          >
            تسجيل الدخول <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </motion.div>
    </div>
  );
};;

// Accept the new props
const StudentDashboard = ({ studentInfo, uploadedGrades, onUpload, isAdvisorView }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("لم يتم رفع ملف بعد");
  // --- NEW STATES FOR EDITING ---
  const [isEditMode, setIsEditMode] = useState(false);
  const [editableSchedule, setEditableSchedule] = useState(null);

  // NEW: State to hold courses that were deleted from the schedule
  const [unassignedCourses, setUnassignedCourses] = useState([]);

  // When the API returns the result, we need to save it to our editable state!
  // Find your handleGenerate function, and right below setResult(data), add:
  // setEditableSchedule(data.schedule);

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const jsonData = JSON.parse(event.target.result);
        const formattedGrades = {};

        jsonData.forEach(item => {
          const cleanCode = item.code.trim();
          if (cleanCode.length <= 10 && !cleanCode.includes("\n")) {
            formattedGrades[cleanCode] = item.grade;
          }
        });

        // Use the passed function to save globally instead of locally
        if (onUpload) {
          onUpload(formattedGrades);
          setUploadStatus(" تم قراءة وتنظيف الملف بنجاح!");
        }
      } catch (error) {
        setUploadStatus(" خطأ في قراءة الملف.");
      }
    };
    reader.readAsText(file);
  };

  // ... (keep your handleGenerate function exactly the same) ...

  // 2. دالة الاتصال بالـ FastAPI الخاص بك
  const handleGenerate = async () => {
    if (!uploadedGrades) {
      alert("الرجاء رفع ملف المواد المجتازة أولاً!");
      return;
    }

    setLoading(true);
    try {
      // حساب عدد الفصول التي أنهاها الطالب بناءً على مستواه
      const semestersDone = parseInt(studentInfo.level) - 1;

      // إرسال الطلب للـ Backend
      const response = await fetch("http://localhost:8000/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          grades: uploadedGrades,
          num_semesters_done: semestersDone > 0 ? semestersDone : 1
        })
      });

      if (!response.ok) throw new Error("حدث خطأ في الخادم");

      const data = await response.json();

      // حفظ الجدول المقترح لعرضه
      setResult(data);
      setEditableSchedule(data.schedule);
      setUnassignedCourses([]);

    } catch (error) {
      console.error(error);
      alert("فشل الاتصال بالخادم. تأكد من تشغيل api.py");
    } finally {
      setLoading(false);
    }
  };
  // --- DRAG AND DROP LOGIC ---
  // --- UPGRADED DRAG AND DROP LOGIC ---

  const handleDragStart = (e, source, courseCode) => {
    // 'source' will either be a semester index (0, 1, 2) or the word "unassigned"
    e.dataTransfer.setData("source", source);
    e.dataTransfer.setData("courseCode", courseCode);
  };

  const handleDrop = (e, targetSemIndex) => {
    e.preventDefault();
    const source = e.dataTransfer.getData("source");
    const courseCode = e.dataTransfer.getData("courseCode");

    if (source === String(targetSemIndex)) return; // Dropped in the same place

    if (source === 'unassigned') {
      // 1. Moving from the Unassigned Pool back into a semester
      const courseToMove = unassignedCourses.find(c => c.code === courseCode);

      setUnassignedCourses(prev => prev.filter(c => c.code !== courseCode)); // Remove from pool

      setEditableSchedule(prev => {
        const newSchedule = JSON.parse(JSON.stringify(prev));
        newSchedule[targetSemIndex].courses.push(courseToMove);
        newSchedule[targetSemIndex].total_hours += courseToMove.hours;
        return newSchedule;
      });

    } else {
      // 2. Moving between two semesters
      const sourceSemIndex = parseInt(source);

      setEditableSchedule(prev => {
        const newSchedule = JSON.parse(JSON.stringify(prev));
        const courseIndex = newSchedule[sourceSemIndex].courses.findIndex(c => c.code === courseCode);
        const courseToMove = newSchedule[sourceSemIndex].courses[courseIndex];

        newSchedule[sourceSemIndex].courses.splice(courseIndex, 1);
        newSchedule[sourceSemIndex].total_hours -= courseToMove.hours;

        newSchedule[targetSemIndex].courses.push(courseToMove);
        newSchedule[targetSemIndex].total_hours += courseToMove.hours;

        return newSchedule;
      });
    }
  };

  const handleDeleteCourse = (semIndex, courseCode) => {
    // 1. Find the exact course we are deleting FIRST
    const courseToDelete = editableSchedule[semIndex].courses.find(c => c.code === courseCode);
    if (!courseToDelete) return;

    // 2. Add it to the Holding Pool (With a safety check to prevent duplicates!)
    setUnassignedCourses(prevUnassigned => {
      // If the course is already in the pool, don't add it again
      if (prevUnassigned.some(c => c.code === courseCode)) return prevUnassigned;
      return [...prevUnassigned, courseToDelete];
    });

    // 3. Remove it from the schedule
    setEditableSchedule(prevSchedule => {
      const newSchedule = JSON.parse(JSON.stringify(prevSchedule));
      const courseIndex = newSchedule[semIndex].courses.findIndex(c => c.code === courseCode);

      if (courseIndex !== -1) {
        newSchedule[semIndex].total_hours -= newSchedule[semIndex].courses[courseIndex].hours;
        newSchedule[semIndex].courses.splice(courseIndex, 1);
      }

      return newSchedule;
    });
  };

  // NEW: Allow dragging courses into the Holding Pool to delete them
  const handleDropToUnassigned = (e) => {
    e.preventDefault();
    const source = e.dataTransfer.getData("source");
    const courseCode = e.dataTransfer.getData("courseCode");

    if (source === 'unassigned') return;

    const sourceSemIndex = parseInt(source);
    handleDeleteCourse(sourceSemIndex, courseCode);
  };

  // --- PDF EXPORT LOGIC ---
  // --- UPGRADED PDF EXPORT LOGIC ---
  const handleExportPDF = () => {
    // 1. Find the exact section we want to turn into a PDF
    const element = document.getElementById('printable-schedule');

    // 2. Configure the PDF settings
    const opt = {
      margin: 15,
      filename: `Academic_Plan_${result.predicted_profile}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true }, // scale: 2 makes the text very sharp
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    // 3. Generate and automatically download!
    html2pdf().set(opt).from(element).save();
  };

  const TOTAL_COURSES_REQUIRED = 59; // <-- Change this to the real number!

  let progressPercentage = 0;
  if (uploadedGrades) {
    const passedCoursesCount = Object.values(uploadedGrades).filter(g => String(g).toUpperCase() !== 'F').length;
    progressPercentage = Math.min(Math.round((passedCoursesCount / TOTAL_COURSES_REQUIRED) * 100), 100);
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="print:hidden space-y-6"> {/* <--- ADD THIS LINE */}
        <header className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div>
            <h2 className="text-xl font-bold text-slate-800">مرحباً، {studentInfo.name}</h2>
            <p className="text-slate-500">الرقم الجامعي: {studentInfo.id}</p>
          </div>
          <div className="bg-green-100 text-green-700 px-4 py-2 rounded-full font-bold">مستوى {studentInfo.level}</div>
        </header>

        {/* If it's NOT the advisor, show the upload box */}
        {!isAdvisorView && (
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 text-center">
            <h3 className="flex items-center justify-center gap-2 font-bold mb-4 text-slate-700">
              <Upload className="w-5 h-5 text-blue-500" /> رفع السجل الأكاديمي (JSON)
            </h3>

            <input type="file" accept=".json" onChange={handleFileUpload} className="hidden" id="file-upload" />
            <label htmlFor="file-upload" className="block border-2 border-dashed border-blue-200 rounded-xl p-8 cursor-pointer hover:bg-blue-50 transition-colors">
              <FileText className="w-12 h-12 text-blue-400 mx-auto mb-3" />
              <p className="text-slate-600 font-bold">اضغط هنا لاختيار ملف JSON</p>
              <p className="text-sm text-slate-400 mt-2">{uploadStatus}</p>
            </label>
          </div>
        )}

        {/* If grades are uploaded, show a success summary box to both student and advisor */}
        {uploadedGrades && (
          <div className="bg-green-50 p-4 rounded-xl border border-green-200 flex items-center gap-3 mb-6">
            <CheckCircle2 className="text-green-600 w-6 h-6" />
            <div>
              <h4 className="font-bold text-green-800">السجل الأكاديمي متوفر</h4>
              <p className="text-sm text-green-600">يحتوي على {Object.keys(uploadedGrades).length} مادة دراسية.</p>
            </div>
          </div>
        )}

        {/* NEW & IMPROVED: Academic History View (Visible ONLY to Advisor) */}
        {uploadedGrades && isAdvisorView && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 mb-6"
          >
            <div className="flex justify-between items-end mb-6 border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-600" /> السجل الأكاديمي للطالب
              </h3>

              {/* NEW FEATURE: Degree Progress Tracker */}
              {/* NEW FEATURE: Degree Progress Tracker */}
              <div className="w-1/3 text-left">
                <div className="flex justify-between text-xs text-slate-500 mb-1 font-bold">
                  <span>نسبة الإنجاز التقريبية</span>
                  <span className="text-blue-600">{progressPercentage}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2.5 rounded-full transition-all duration-1000 ease-out"
                    style={{ width: `${progressPercentage}%` }}
                  ></div>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">بناءً على {TOTAL_COURSES_REQUIRED} مقرر للتخرج</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-72 overflow-y-auto pr-2">
              {Object.entries(uploadedGrades).map(([code, grade]) => {
                const safeGrade = String(grade || '').toUpperCase();

                let colorClass = 'bg-slate-100 text-slate-700';
                if (safeGrade.includes('A')) colorClass = 'bg-green-100 text-green-800';
                else if (safeGrade.includes('B')) colorClass = 'bg-blue-100 text-blue-800';
                else if (safeGrade.includes('C')) colorClass = 'bg-yellow-100 text-yellow-800';
                else if (safeGrade.includes('D')) colorClass = 'bg-orange-100 text-orange-800';
                else if (safeGrade.includes('F')) colorClass = 'bg-red-100 text-red-800';

                // Lookup the name, or provide a default fallback
                const courseName = courseDictionary[code] || "مقرر دراسي";

                return (
                  <div key={code} className="bg-white p-3.5 rounded-xl border border-slate-200 flex justify-between items-center hover:border-blue-300 hover:shadow-md transition-all duration-200">
                    <div className="flex flex-col pl-2">
                      {/* Course Name is now primary, bold, and larger */}
                      <span className="font-bold text-slate-900 text-sm leading-tight">{courseName}</span>

                      {/* Course Code is now a neat secondary tag */}
                      <span className="font-mono text-[11px] text-slate-500 bg-slate-100 w-fit px-1.5 py-0.5 rounded mt-1.5 border border-slate-200">
                        {code}
                      </span>
                    </div>

                    <span className={`font-black px-3 py-1.5 rounded-lg text-sm shadow-sm border ${colorClass.replace('bg-', 'border-').replace('100', '200')} ${colorClass}`}>
                      {grade}
                    </span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* The Generation Button */}
        <button
          onClick={handleGenerate}
          disabled={loading || !uploadedGrades}
          className={`w-full py-4 text-white font-bold rounded-2xl shadow-xl transition-all ${loading || !uploadedGrades ? 'bg-slate-400 cursor-not-allowed' : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:opacity-90'}`}
        >
          {loading
            ? "جاري التحليل وبناء الخطة..."
            : isAdvisorView
              ? "تحليل السجل وإصدار التوصيات ✨" // Dynamic text if advisor is viewing
              : "توليد الخطة الدراسية المثالية ✨"
          }
        </button>

        {/* عرض النتائج القادمة من الباك اند */}
        {/* عرض النتائج القادمة من الباك اند */}
        {/* عرض النتائج القادمة من الباك اند */}
      </div> {/* <--- ADD THIS CLOSING DIV */}
      {result && editableSchedule && (
        <div className="mt-8 space-y-6" id="printable-schedule">

          {/* Header Box - Added "print:hidden" so it disappears in the PDF! */}
          <div className={`print:hidden p-5 rounded-2xl border flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-sm ${isAdvisorView ? 'bg-slate-900 text-white border-slate-800' : 'bg-indigo-50 border-indigo-100'
            }`}>
            <div>
              <p className={`font-bold text-lg ${isAdvisorView ? 'text-white' : 'text-indigo-800'}`}>
                التصنيف المتوقع:
                <span className={`px-3 py-1 rounded-lg mx-2 text-sm ${isAdvisorView ? 'bg-blue-600 text-white' : 'bg-indigo-200 text-indigo-900'}`}>
                  {result.predicted_profile}
                </span>
              </p>
              <p className={`text-sm mt-2 ${isAdvisorView ? 'text-slate-400' : 'text-indigo-600'}`}>
                المعدل التقريبي: {result.gpa} | الفصول المتبقية: {result.remaining_semesters}
              </p>
            </div>

            {/* Student PDF Export Button */}
            {!isAdvisorView && (
              <button
                onClick={handleExportPDF}
                data-html2canvas-ignore="true" /* <--- ADD THIS */
                className="print:hidden bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-md"
              >
                <FileText className="w-4 h-4" /> تصدير كملف PDF
              </button>
            )}

            {/* Advisor Insights Box */}
            {isAdvisorView && (
              <div className="bg-slate-800 p-4 rounded-xl text-xs text-slate-300 border border-slate-700 md:max-w-xs w-full print:hidden">
                <strong className="text-blue-400 flex items-center gap-1 mb-2 text-sm">
                  ✨ تحليل النظام الذكي:
                </strong>
                تم بناء الخطة بتوزيع متوازن للساعات. يمكنك تعديل الخطة يدوياً بسحب وإفلات المواد بين الفصول.
              </div>
            )}
          </div>

          {/* NEW: Unassigned Courses (Holding Pool) - Visible only in Edit Mode */}
          {isEditMode && unassignedCourses.length > 0 && (
            <div
              data-html2canvas-ignore="true"
              className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-2xl p-5 print:hidden"
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDropToUnassigned}
            >
              <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2">
                📥 المواد المستبعدة
                <span className="text-xs font-normal text-slate-500">
                  (اسحب المادة لإعادتها للجدول)
                </span>
              </h4>
              <div className="flex flex-wrap gap-3">
                {unassignedCourses.map(c => {
                  const nameFromDict = courseDictionary ? courseDictionary[c.code] : c.name;
                  return (
                    <div
                      key={c.code}
                      draggable
                      onDragStart={(e) => handleDragStart(e, 'unassigned', c.code)}
                      className="bg-white border border-slate-200 shadow-sm p-3 rounded-xl flex items-center gap-3 cursor-grab active:cursor-grabbing hover:border-blue-300 transition-colors"
                    >
                      <span className="text-slate-400">⋮⋮</span>
                      <div className="flex flex-col">
                        <span className="font-bold text-slate-800 text-sm">{nameFromDict}</span>
                        <span className="text-xs text-slate-500">{c.code} • {c.hours} ساعات</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* The Schedule Grid (Now Editable!) */}
          <div className="grid md:grid-cols-2 gap-4">
            {editableSchedule.map((sem, semIndex) => (
              <div
                key={semIndex}
                onDragOver={(e) => isEditMode ? e.preventDefault() : null}
                onDrop={(e) => isEditMode ? handleDrop(e, semIndex) : null}
                className={`bg-white border p-6 rounded-2xl shadow-sm transition-all duration-200 ${isEditMode ? 'border-blue-400 border-dashed bg-blue-50/30' : 'border-slate-200 hover:shadow-md'
                  }`}
              >
                <div className="flex justify-between items-center mb-5 border-b border-slate-100 pb-3">
                  <h4 className="font-bold text-slate-800 text-lg">الفصل {sem.semester}</h4>
                  <span className={`text-xs font-bold px-3 py-1.5 rounded-lg border ${sem.total_hours > 20 ? 'bg-red-50 text-red-700 border-red-200' :
                    sem.total_hours < 12 ? 'bg-orange-50 text-orange-700 border-orange-200' :
                      'bg-blue-50 text-blue-700 border-blue-100'
                    }`}>
                    {sem.total_hours} ساعة
                  </span>
                </div>

                <ul className="space-y-3 min-h-[50px]">
                  {sem.courses.map(c => {
                    const nameFromDict = courseDictionary ? courseDictionary[c.code] : c.name;
                    return (
                      <li
                        key={c.code}
                        draggable={isEditMode}
                        onDragStart={(e) => handleDragStart(e, semIndex, c.code)}
                        className={`flex flex-col bg-slate-50 p-3 rounded-xl border border-slate-100 relative group ${isEditMode ? 'cursor-grab active:cursor-grabbing hover:border-blue-300 hover:shadow-sm' : ''
                          }`}
                      >
                        <div className="flex justify-between items-start mb-1 pr-6">
                          {/* Drag Indicator Icon */}
                          {isEditMode && (
                            <span className="absolute right-2 top-3 text-slate-400">⋮⋮</span>
                          )}
                          <span className="font-bold text-slate-800 text-sm">{nameFromDict}</span>
                          <span className="text-slate-500 font-mono text-xs bg-white px-2 py-1 rounded border border-slate-200">
                            {c.code}
                          </span>
                        </div>
                        <span className="text-slate-400 text-xs text-left w-full pl-1">{c.hours} ساعات</span>

                        {/* Delete Button */}
                        {isEditMode && (
                          <button
                            onClick={() => handleDeleteCourse(semIndex, c.code)}
                            className="absolute left-2 top-2 text-red-400 hover:text-red-600 bg-red-50 hover:bg-red-100 rounded p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            ✕
                          </button>
                        )}
                      </li>
                    );
                  })}
                  {sem.courses.length === 0 && (
                    <div className="text-center text-slate-400 text-xs py-4 border-2 border-dashed border-slate-200 rounded-xl">
                      اسحب مادة هنا
                    </div>
                  )}
                </ul>
              </div>
            ))}
          </div>

          {/* Action Buttons - VISIBLE ONLY TO ADVISOR */}
          {isAdvisorView && (
            <div data-html2canvas-ignore="true" className="flex flex-col md:flex-row gap-3 pt-6 border-t border-slate-200 mt-6 print:hidden">              <button
              onClick={handleExportPDF}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white py-4 rounded-xl font-bold transition-all shadow-lg shadow-green-100 flex justify-center items-center gap-2"
            >
              <CheckCircle2 className="w-5 h-5" /> اعتماد الخطة وإصدارها كـ PDF
            </button>

              <button
                onClick={() => setIsEditMode(!isEditMode)}
                className={`flex-1 border-2 py-4 rounded-xl font-bold transition-all ${isEditMode
                  ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-200'
                  : 'bg-white border-slate-200 hover:border-slate-300 text-slate-700'
                  }`}
              >
                {isEditMode ? '✅ إنهاء التعديل' : '✏️ تعديل الخطة يدوياً'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Accept the allStudentGrades object
const AdvisorDashboard = ({ onSelectStudent, allStudentGrades, studentProfiles }) => {
  // 1. Get ONLY the IDs of students who have uploaded a file
  const uploadedStudentIds = Object.keys(allStudentGrades);

  // 2. Match those IDs to their real profiles
  const activeStudents = uploadedStudentIds.map(id => studentProfiles[id]).filter(Boolean);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <Users className="text-blue-600" /> لوحة تحكم المرشد
      </h2>

      {/* Show a message if no one has uploaded yet */}
      {activeStudents.length === 0 ? (
        <div className="bg-white p-12 rounded-2xl shadow-sm border border-slate-100 text-center">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 font-bold text-lg">لا يوجد طلاب حالياً</p>
          <p className="text-slate-400 text-sm mt-1">الطلاب الذين يقومون برفع سجلاتهم الأكاديمية سيظهرون هنا تلقائياً.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {activeStudents.map(s => (
            <motion.div
              whileHover={{ x: 10 }}
              key={s.id}
              className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex justify-between items-center cursor-pointer hover:bg-blue-50 transition-colors"
              onClick={() => onSelectStudent(s)}
            >
              <div className="flex items-center gap-4">
                <div className="bg-slate-200 w-12 h-12 rounded-full flex items-center justify-center font-bold text-slate-600">
                  {s.name[0]}
                </div>
                <div>
                  <h4 className="font-bold text-slate-800">{s.name}</h4>
                  <p className="text-xs text-slate-500">الرقم الجامعي: {s.id}</p>

                  <span className="text-xs text-green-600 font-bold mt-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> تم رفع السجل (جاهز للتحليل)
                  </span>
                </div>
              </div>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-bold shadow-md transition-colors">
                تحليل الخطة
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};

// --- المكون الرئيسي للمشروع ---

export default function App() {
  const [view, setView] = useState('login');
  const [currentUser, setCurrentUser] = useState(null);
  const [selectedStudent, setSelectedStudent] = useState(null);

  const [allStudentGrades, setAllStudentGrades] = useState({});
  // NEW: State to remember the profiles of students who log in
  const [studentProfiles, setStudentProfiles] = useState({});

  const handleLogin = (id, pass, name) => {
    if (pass === '1234') {
      const newProfile = {
        id: id || '000',
        name: name || 'طالب',
        gpa: 'N/A',
        level: '7'
      };
      setCurrentUser(newProfile);

      // Save their profile into our "database"
      setStudentProfiles(prev => ({ ...prev, [newProfile.id]: newProfile }));

      setView('student');
    } else if (id === '222' && pass === '4321') {
      setView('advisor');
    } else {
      alert('خطأ في البيانات!');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans" dir="rtl">
      {view !== 'login' && (
        <nav className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center print:hidden">          <span className="font-black text-blue-600 text-xl italic">AI_ADVISOR</span>
          <button onClick={() => setView('login')} className="text-slate-500 flex items-center gap-1 hover:text-red-500 transition-colors">
            خروج <LogOut className="w-4 h-4" />
          </button>
        </nav>
      )}

      {view === 'login' && <LoginPage onLogin={handleLogin} />}

      {view === 'student' && (
        <StudentDashboard
          studentInfo={currentUser}
          uploadedGrades={allStudentGrades[currentUser.id]}
          onUpload={(grades) => setAllStudentGrades(prev => ({ ...prev, [currentUser.id]: grades }))}
          isAdvisorView={false}
        />
      )}

      {view === 'advisor' && !selectedStudent && (
        <AdvisorDashboard
          onSelectStudent={(s) => setSelectedStudent(s)}
          allStudentGrades={allStudentGrades}
          studentProfiles={studentProfiles} // Pass the profiles to the advisor
        />
      )}

      {selectedStudent && (
        <div className="p-4">
          <button onClick={() => setSelectedStudent(null)} className="mb-4 text-blue-600 font-bold">← العودة للطلاب</button>
          <StudentDashboard
            studentInfo={selectedStudent}
            uploadedGrades={allStudentGrades[selectedStudent.id]}
            isAdvisorView={true}
          />
        </div>
      )}
    </div>
  );
}
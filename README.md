# 🎓 AI Academic Advisor (المُرشد الأكاديمي الذكي)

An intelligent, full-stack degree planning system designed to analyze student transcripts, predict academic trajectories, and dynamically generate optimized semester-by-semester graduation plans. 

Built with **React**, **FastAPI**, and **Machine Learning**, this system replaces static academic advising with a personalized, data-driven experience.

## ✨ Key Features

* 🧠 **AI Performance Prediction:** Uses a trained Random Forest model to analyze a student's past grades (handling complex dual-scaling from 100-point to 5.0 GPA systems) and classifies their academic profile (Excellent, Good, Average, Weak).
* ⚙️ **Smart Schedule Generation (Knapsack Algorithm):** Automatically builds optimal future semesters. It dynamically restricts maximum credit hours based on the AI's prediction (e.g., struggling students are capped at 15 hours, while excellent students can take 20 hours).
* 🔗 **Prerequisite Enforcement:** Utilizes a Directed Acyclic Graph (DAG) to map the university curriculum, ensuring no course is scheduled before its prerequisites are passed.
* 🖱️ **Interactive Drag-and-Drop Dashboard:** Advisors and students can manually tweak the generated plan by dragging courses between semesters, with real-time hour calculation and error warnings.
* 📄 **1-Click PDF Export:** Generates clean, professional PDF academic plans instantly using `html2pdf.js`.
* 🛡️ **Bulletproof Data Ingestion:** Features a custom regex parser that handles messy Arabic/English text inputs and intelligently converts various grade formats (Letters, Percentages, and 5.0 GPA scales) into actionable data.

## 🛠️ Tech Stack

**Frontend:**
* React.js
* Tailwind CSS (for modern, responsive styling)
* HTML5 Native Drag-and-Drop API
* `html2pdf.js` (for client-side PDF generation)

**Backend:**
* Python (FastAPI)
* Scikit-Learn & Joblib (Machine Learning)
* Pandas & NumPy (Data Processing)
* NetworkX (Course Prerequisite Graphing)

## 🚀 How to Run the Project Locally

### 1. Start the Backend (FastAPI)
```bash
# Navigate to the backend folder
cd backend 

# Install dependencies
pip install fastapi uvicorn pandas numpy scikit-learn networkx

# Run the server
uvicorn api:app --reload
```
*The API will run on `http://127.0.0.1:8000`*

### 2. Start the Frontend (React)
```bash
# Open a new terminal and navigate to the frontend folder
cd frontend

# Install Node modules
npm install

# Start the React app
npm start
```
*The dashboard will run on `http://localhost:3000`*

## 📝 Usage
1. Log in to the dashboard.
2. Upload a student's academic history via a structured JSON file.
3. The system processes the grades, predicts the student's profile, and generates a flawless graduation plan.
4. Use the "Edit Plan" feature to drag and drop courses or remove them into the "Holding Pool".
5. Export the final approved plan to PDF.

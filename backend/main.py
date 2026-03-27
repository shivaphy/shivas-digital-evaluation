import os
import json
import base64
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional, List, Dict
import google.generativeai as genai
import uvicorn

# --- CONFIG ---
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE"))

app = FastAPI(title="Tri-Phase Evaluation API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOCK DATABASES ---
USER_DB = {
    "admin_faculty": {"password": "pass123", "role": "faculty", "name": "Dr. Priya Sharma"},
    "hod_user":      {"password": "hod789",  "role": "hod",     "name": "Prof. Ramesh Kumar"},
    "student_001":   {"password": "stu001",  "role": "student",  "name": "Arjun Mehta"},
}

# In-memory evaluation store (replace with DB in production)
EVALUATIONS: Dict[str, dict] = {}
SESSIONS: Dict[str, dict] = {}  # session_id -> {question_paper, scheme, script}

# --- DATA MODELS ---
class MarksEntry(BaseModel):
    student_id: str
    evaluator_type: str  # 'AI', 'FACULTY', 'STUDENT'
    marks: dict          # {"q1a": 4.5, "q1b": 3.5, "total": 8.0}
    justification: Optional[str] = None

class FinalizeRequest(BaseModel):
    student_id: str
    selected_evaluator: str  # 'AI', 'FACULTY', 'STUDENT', 'MODERATED'
    moderated_marks: Optional[dict] = None
    moderator: str

class SchemeOfEvaluation(BaseModel):
    questions: List[dict]  # [{id: "q1a", max_marks: 5, keywords: [...], model_answer: "..."}]

# --- AUTH ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = USER_DB.get(form_data.username)
    if not user or form_data.password != user["password"]:
        raise HTTPException(status_code=401, detail="Invalid Credentials")
    return {
        "access_token": form_data.username,
        "token_type": "bearer",
        "role": user["role"],
        "name": user["name"]
    }

# --- UPLOAD SESSION ---
@app.post("/upload-session")
async def upload_session(
    student_id: str = Form(...),
    question_paper: UploadFile = File(...),
    scheme: UploadFile = File(...),
    answer_script: UploadFile = File(...)
):
    """Upload PDFs for a student evaluation session."""
    qp_bytes = await question_paper.read()
    scheme_bytes = await scheme.read()
    script_bytes = await answer_script.read()

    SESSIONS[student_id] = {
        "question_paper_b64": base64.b64encode(qp_bytes).decode(),
        "scheme_b64": base64.b64encode(scheme_bytes).decode(),
        "script_b64": base64.b64encode(script_bytes).decode(),
        "script_filename": answer_script.filename,
    }
    return {"status": "uploaded", "student_id": student_id}

# --- AI ANALYSIS ---
@app.post("/run-ai-analysis")
async def run_ai_analysis(student_id: str):
    """
    Run Gemini Vision on the answer script against the scheme of evaluation.
    Falls back to mock data if no session uploaded or API key not set.
    """
    session = SESSIONS.get(student_id)

    if session and os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "YOUR_GEMINI_API_KEY_HERE":
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")

            script_bytes = base64.b64decode(session["script_b64"])
            scheme_bytes = base64.b64decode(session["scheme_b64"])

            prompt = """
You are an expert academic evaluator. You have been given:
1. A student's handwritten answer script (PDF/Image)
2. A Scheme of Evaluation (rubric)

Your task:
- Read the handwritten answers carefully using your vision capabilities.
- Compare each answer against the scheme of evaluation.
- Award marks for each sub-question (q1a, q1b, q1c or q2a, q2b, q2c).
- If the student answered both Q1 and Q2 (OR choice), evaluate both and flag it.
- Provide a confidence score (0-1) for your evaluation.
- Be strict but fair, giving partial credit where steps are shown.

Return ONLY valid JSON in this exact format:
{
  "q1a": {"marks": 4.5, "max": 5, "feedback": "Good explanation of...", "confidence": 0.9},
  "q1b": {"marks": 3.5, "max": 5, "feedback": "Missing key formula...", "confidence": 0.85},
  "total": 8.0,
  "overall_confidence": 0.87,
  "choice_conflict": false,
  "htr_text": "Extracted handwritten text here...",
  "general_feedback": "The student demonstrates understanding but lacks..."
}
"""
            # Send script image to Gemini
            response = model.generate_content([
                prompt,
                {"mime_type": "application/pdf", "data": script_bytes}
            ])
            result = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
            return {"status": "success", "ai_eval": result, "source": "gemini"}

        except Exception as e:
            # Fall through to mock
            print(f"Gemini error: {e}")

    # Mock response for demo/testing
    mock = {
        "q1a": {"marks": 4.5, "max": 5, "feedback": "Strong conceptual understanding. Formula correctly applied.", "confidence": 0.92},
        "q1b": {"marks": 3.5, "max": 5, "feedback": "Partial credit: missing final step in derivation.", "confidence": 0.85},
        "total": 8.0,
        "overall_confidence": 0.88,
        "choice_conflict": False,
        "htr_text": "[Mock HTR] Student answered Q1a and Q1b. Showed working for both parts.",
        "general_feedback": "Good attempt. Review derivation steps for completeness."
    }
    return {"status": "success", "ai_eval": mock, "source": "mock"}

# --- SUBMIT MARKS ---
@app.post("/submit-marks")
async def submit_marks(entry: MarksEntry):
    if entry.student_id not in EVALUATIONS:
        EVALUATIONS[entry.student_id] = {}

    EVALUATIONS[entry.student_id][entry.evaluator_type] = {
        "marks": entry.marks,
        "justification": entry.justification,
        "submitted_by": entry.evaluator_type
    }
    return {"status": "success", "message": f"{entry.evaluator_type} marks recorded for {entry.student_id}"}

# --- GET COMPARISON (HOD Dashboard) ---
@app.get("/comparison/{student_id}")
async def get_comparison(student_id: str):
    evals = EVALUATIONS.get(student_id, {})
    faculty = evals.get("FACULTY", {})
    ai = evals.get("AI", {})
    student = evals.get("STUDENT", {})

    def get_total(e):
        return float(e.get("marks", {}).get("total", 0)) if e else 0

    f_total = get_total(faculty)
    a_total = get_total(ai)
    s_total = get_total(student)

    # Deviation check
    deviation = abs(f_total - a_total) / max(f_total, 1) * 100
    flagged = deviation > 15

    return {
        "student_id": student_id,
        "faculty": faculty,
        "ai": ai,
        "student": student,
        "deviation_percent": round(deviation, 1),
        "flagged": flagged,
        "finalized": evals.get("FINALIZED")
    }

# --- FINALIZE (HOD) ---
@app.post("/finalize")
async def finalize(req: FinalizeRequest):
    if req.student_id not in EVALUATIONS:
        EVALUATIONS[req.student_id] = {}

    if req.selected_evaluator == "MODERATED" and req.moderated_marks:
        final_marks = req.moderated_marks
    else:
        eval_data = EVALUATIONS[req.student_id].get(req.selected_evaluator, {})
        final_marks = eval_data.get("marks", {})

    EVALUATIONS[req.student_id]["FINALIZED"] = {
        "marks": final_marks,
        "selected_from": req.selected_evaluator,
        "finalized_by": req.moderator
    }
    return {"status": "finalized", "final_marks": final_marks}

# --- LIST STUDENTS ---
@app.get("/students")
async def list_students():
    all_students = [
        {"id": "STU-8829", "name": "Arjun Mehta",    "status": "pending",  "script_pages": 8},
        {"id": "STU-8830", "name": "Priya Nair",     "status": "graded",   "script_pages": 6},
        {"id": "STU-8831", "name": "Rahul Singh",    "status": "flagged",  "script_pages": 10},
        {"id": "STU-8832", "name": "Ananya Reddy",   "status": "pending",  "script_pages": 7},
    ]
    for s in all_students:
        s["has_eval"] = s["id"] in EVALUATIONS
    return all_students

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

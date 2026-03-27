-- Tri-Phase Digital Evaluation System — Database Schema v2.0

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(200),
    role VARCHAR(20) NOT NULL CHECK (role IN ('faculty', 'hod', 'student')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Exam sessions (per student per exam)
CREATE TABLE exam_sessions (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL,
    exam_name VARCHAR(200),
    question_paper_path TEXT,
    scheme_path TEXT,
    script_path TEXT,
    htr_text TEXT,           -- Extracted handwritten text
    choice_conflict BOOLEAN DEFAULT FALSE,  -- Student answered both OR options
    created_at TIMESTAMP DEFAULT NOW()
);

-- Evaluations (one row per evaluator per student)
CREATE TABLE evaluations (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES exam_sessions(id),
    student_id VARCHAR(50) NOT NULL,
    evaluator_type VARCHAR(20) NOT NULL CHECK (evaluator_type IN ('AI', 'FACULTY', 'STUDENT')),
    evaluator_name VARCHAR(200),

    -- Sub-question marks (dynamic, stored as JSONB for flexibility)
    marks JSONB NOT NULL DEFAULT '{}',
    -- e.g. {"q1a": 4.5, "q1b": 3.5, "total": 8.0}

    -- Per-question max limits
    max_marks JSONB NOT NULL DEFAULT '{}',

    justification TEXT,
    ai_confidence FLOAT,         -- Only for AI evaluator
    ai_htr_text TEXT,            -- HTR output from AI
    ai_feedback JSONB,           -- Per-question AI feedback

    submitted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(student_id, evaluator_type)
);

-- Final moderated decisions by HoD
CREATE TABLE final_decisions (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(50) NOT NULL UNIQUE,
    session_id INT REFERENCES exam_sessions(id),
    selected_evaluator VARCHAR(20),   -- Which evaluator's marks were chosen
    final_marks JSONB NOT NULL,
    deviation_percent FLOAT,
    moderator VARCHAR(200),
    notes TEXT,
    finalized_at TIMESTAMP DEFAULT NOW()
);

-- Audit log
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100),
    student_id VARCHAR(50),
    performed_by VARCHAR(200),
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Sample index
CREATE INDEX idx_evals_student ON evaluations(student_id);
CREATE INDEX idx_finals_student ON final_decisions(student_id);

from flask import Blueprint, request, jsonify, session
import json
from ..models.database import get_db
from .interview import call_ai_api, generate_questions

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    uid = session['user_id']
    db = get_db()

    total = db.execute('SELECT COUNT(*) as c FROM interviews WHERE user_id = ? AND completed = 1', (uid,)).fetchone()['c']
    avg_row = db.execute('SELECT AVG(score) as avg FROM interviews WHERE user_id = ? AND completed = 1', (uid,)).fetchone()
    avg_score = round(avg_row['avg'] or 0, 1)

    recent = db.execute(
        'SELECT role, topic, score, date FROM interviews WHERE user_id = ? AND completed = 1 ORDER BY date DESC LIMIT 7',
        (uid,)
    ).fetchall()

    topics = db.execute(
        'SELECT topic, AVG(score) as avg_score, COUNT(*) as count FROM interviews WHERE user_id = ? AND completed = 1 GROUP BY topic ORDER BY avg_score ASC',
        (uid,)
    ).fetchall()

    weak = [dict(t) for t in topics[:3]]
    strong = [dict(t) for t in topics[-3:]]

    streak = db.execute(
        "SELECT COUNT(DISTINCT date(date)) as days FROM interviews WHERE user_id = ? AND completed = 1 AND date >= date('now', '-30 days')",
        (uid,)
    ).fetchone()['days']

    db.close()

    return jsonify({
        'total_interviews': total,
        'average_score': avg_score,
        'streak_days': streak,
        'recent': [dict(r) for r in recent],
        'weak_areas': weak,
        'strong_areas': strong
    })

@dashboard_bp.route('/api/dashboard/progress', methods=['GET'])
def get_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    uid = session['user_id']
    db = get_db()

    data = db.execute(
        "SELECT date(date) as day, AVG(score) as avg_score, COUNT(*) as count FROM interviews WHERE user_id = ? AND completed = 1 GROUP BY date(date) ORDER BY day DESC LIMIT 14",
        (uid,)
    ).fetchall()
    db.close()

    return jsonify([dict(d) for d in data])

@dashboard_bp.route('/api/resume/upload', methods=['POST'])
def upload_resume():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    if 'resume' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['resume']
    filename = file.filename or 'resume.txt'
    content = ""

    try:
        if filename.lower().endswith('.pdf'):
            try:
                import fitz
                pdf_bytes = file.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                for page in doc:
                    content += page.get_text()
                doc.close()
            except ImportError:
                content = file.read().decode('utf-8', errors='ignore')
        else:
            content = file.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return jsonify({'error': f'Could not read file: {str(e)}'}), 400

    content = content[:5000]

    db = get_db()
    db.execute(
        'INSERT OR REPLACE INTO resumes (user_id, filename, content) VALUES (?, ?, ?)',
        (session['user_id'], filename, content)
    )
    db.commit()
    db.close()

    return jsonify({'success': True, 'filename': filename, 'length': len(content)})

@dashboard_bp.route('/api/resume/interview', methods=['POST'])
def resume_interview():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    db = get_db()
    resume = db.execute('SELECT * FROM resumes WHERE user_id = ? ORDER BY uploaded_at DESC LIMIT 1', (session['user_id'],)).fetchone()

    if not resume:
        db.close()
        return jsonify({'error': 'No resume found. Please upload your resume first.'}), 404

    system = """You are an expert technical interviewer. Generate resume-based interview questions as JSON.
Return ONLY valid JSON array. No markdown.
Format: [{"question": "...", "type": "experience|skill|project|behavioral", "hint": "..."}]"""

    prompt = f"""Based on this resume, generate 5 targeted interview questions:

{resume['content'][:3000]}

Ask about specific experiences, skills, projects, and achievements mentioned. Make questions challenging."""

    response = call_ai_api(prompt, system)
    try:
        cleaned = response.strip().replace('```json', '').replace('```', '').strip()
        questions = json.loads(cleaned)
    except Exception:
        questions = [{"question": "Walk me through your most recent project.", "type": "experience", "hint": "Be specific"}]

    cursor = db.execute(
        'INSERT INTO interviews (user_id, role, topic, difficulty, total_questions, interview_type) VALUES (?, ?, ?, ?, ?, ?)',
        (session['user_id'], 'Resume Based', 'General', 'medium', len(questions), 'resume')
    )
    interview_id = cursor.lastrowid
    db.commit()
    db.close()

    return jsonify({'interview_id': interview_id, 'questions': questions, 'total': len(questions)})

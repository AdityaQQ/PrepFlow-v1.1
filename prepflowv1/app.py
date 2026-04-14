from flask import Flask, render_template, session, redirect, url_for, jsonify
from flask_cors import CORS
from config import Config
from models.database import init_db
from routes.auth import auth_bp
from routes.interview import interview_bp
from routes.dashboard import dashboard_bp
import os

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, supports_credentials=True)

app.register_blueprint(auth_bp)
app.register_blueprint(interview_bp)
app.register_blueprint(dashboard_bp)


@app.route('/api/debug/test-ai')
def test_ai():
    from routes.interview import call_ai_api
    result = call_ai_api(
        'Reply with exactly this JSON: {"status":"working","model":"llama-3.3-70b","app":"PrepFlow"}',
        'Reply with only JSON. No prose.'
    )
    return jsonify({"raw": result, "key": Config.GROQ_API_KEY[:20]+"..."})


@app.route('/')
def index():
    return render_template('index.html', user=session.get('user_name'))


@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return render_template('login.html')


@app.route('/signup')
def signup_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard_page'))
    return render_template('signup.html')


@app.route('/dashboard')
def dashboard_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('dashboard.html', user=session.get('user_name'))


@app.route('/interview')
def interview_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('interview.html', user=session.get('user_name'))


@app.route('/coding')
def coding_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('coding.html', user=session.get('user_name'))


@app.route('/resume')
def resume_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('resume.html', user=session.get('user_name'))


@app.route('/history')
def history_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('history.html', user=session.get('user_name'))


# Initialize DB & session folder
init_db()
os.makedirs('flask_session', exist_ok=True)


# IMPORTANT: No app.run() for Vercel
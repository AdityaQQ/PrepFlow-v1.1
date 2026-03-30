from flask import Blueprint, request, jsonify, session
import hashlib
import os
from models.database import get_db

auth_bp = Blueprint('auth', __name__)

def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return salt.hex() + ':' + key.hex()

def verify_password(stored: str, provided: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(':')
        salt = bytes.fromhex(salt_hex)
        key = hashlib.pbkdf2_hmac('sha256', provided.encode(), salt, 100000)
        return key.hex() == key_hex
    except Exception:
        return False

@auth_bp.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not name or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        db.close()
        return jsonify({'error': 'Email already registered'}), 409

    hashed = hash_password(password)
    db.execute('INSERT INTO users (name, email, password) VALUES (?, ?, ?)', (name, email, hashed))
    db.commit()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    db.close()

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']

    return jsonify({'success': True, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}})

@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    db.close()

    if not user or not verify_password(user['password'], password):
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id'] = user['id']
    session['user_name'] = user['name']
    session['user_email'] = user['email']

    return jsonify({'success': True, 'user': {'id': user['id'], 'name': user['name'], 'email': user['email']}})

@auth_bp.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@auth_bp.route('/api/me', methods=['GET'])
def me():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({
        'id': session['user_id'],
        'name': session['user_name'],
        'email': session['user_email']
    })

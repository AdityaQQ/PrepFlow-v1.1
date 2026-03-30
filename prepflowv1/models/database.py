import sqlite3
import os
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            avatar TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            topic TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            score REAL DEFAULT 0,
            total_questions INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0,
            interview_type TEXT DEFAULT 'standard',
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            interview_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            feedback TEXT,
            score REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (interview_id) REFERENCES interviews(id)
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

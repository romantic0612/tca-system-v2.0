# -*- coding: utf-8 -*-
"""
TCA-System V2.0 数据库Schema
===========================

使用SQLite存储用户和会话数据
账号使用INTEGER类型（学号8位、工号6位）
"""

import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'tca_system.db'

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('student', 'teacher', 'admin_exp', 'admin_sys')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_assignments (
            student_id INTEGER PRIMARY KEY,
            student_name TEXT,
            class_id TEXT,
            pretest_score REAL,
            experiment_group TEXT CHECK(experiment_group IN ('SA', 'EXP', 'AI-AUTO', 'TCA')),
            current_question INTEGER DEFAULT 1,
            total_questions INTEGER DEFAULT 10,
            FOREIGN KEY (student_id) REFERENCES users(user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teacher_overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            teacher_id INTEGER NOT NULL,
            override_type TEXT,
            content TEXT,
            question_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            question_id INTEGER,
            override_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            answer TEXT,
            is_correct INTEGER,
            time_spent INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_states (
            student_id INTEGER PRIMARY KEY,
            current_agent TEXT DEFAULT 'Guide',
            error_streak REAL DEFAULT 0,
            last_error_type TEXT,
            consecutive_correct INTEGER DEFAULT 0,
            last_response_time TEXT,
            last_trigger_level TEXT,
            total_interactions INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES student_assignments(student_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trigger_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            trigger_level TEXT,
            error_type TEXT,
            error_streak_value REAL,
            stagnation_seconds INTEGER,
            detected_keywords TEXT,
            trigger_strength TEXT,
            diagnosis_result TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES student_assignments(student_id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigger_events_student ON trigger_events(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_trigger_events_time ON trigger_events(created_at)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluation_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            student_answer TEXT,
            standard_answer TEXT,
            is_correct INTEGER,
            error_type TEXT,
            score REAL,
            confidence TEXT,
            key_mistake TEXT,
            suggestion TEXT,
            evaluated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES student_assignments(student_id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_eval_records_student ON evaluation_records(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_eval_records_question ON evaluation_records(question_id)')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_switches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            from_agent TEXT,
            to_agent TEXT,
            switch_reason TEXT,
            triggered_by TEXT,
            trigger_event_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES student_assignments(student_id),
            FOREIGN KEY (trigger_event_id) REFERENCES trigger_events(id)
        )
    ''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_switches_student ON agent_switches(student_id)')
    
    try:
        cursor.execute('ALTER TABLE teacher_overrides ADD COLUMN intervention_type TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE teacher_overrides ADD COLUMN diagnosis_context TEXT')
    except:
        pass
    
    try:
        cursor.execute('ALTER TABLE teacher_overrides ADD COLUMN trigger_event_id INTEGER')
    except:
        pass

    try:
        cursor.execute('ALTER TABLE teacher_overrides ADD COLUMN feedback TEXT')
    except:
        pass

    try:
        cursor.execute('ALTER TABLE teacher_overrides ADD COLUMN feedback_at TEXT')
    except:
        pass

    try:
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN override_id INTEGER')
    except:
        pass
    
    conn.commit()

    try:
        cursor.execute('ALTER TABLE student_assignments ADD COLUMN pretest_score REAL')
    except:
        pass

    conn.close()

def create_default_accounts():
    """Create only the minimal accounts needed to enter the system."""
    from ..auth.auth_manager import AuthManager
    auth = AuthManager()

    conn = get_connection()
    cursor = conn.cursor()

    accounts = [
        (900001, 'admin123', 'admin_sys'),
    ]

    for user_id, password, role in accounts:
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            password_hash = auth.hash_password(password)
            cursor.execute(
                'INSERT INTO users (user_id, password_hash, role) VALUES (?, ?, ?)',
                (user_id, password_hash, role)
            )

    conn.commit()
    conn.close()


def create_test_users():
    """Seed demo accounts explicitly for local tests or demos."""
    from ..auth.auth_manager import AuthManager
    auth = AuthManager()

    conn = get_connection()
    cursor = conn.cursor()

    test_users = [
        (20240001, '123456', 'student', '张明', 'SA'),
        (20240002, '123456', 'student', '李华', 'EXP'),
        (20240003, '123456', 'student', '王芳', 'TCA'),
        (20240004, '123456', 'student', '赵强', 'AI-AUTO'),
        (100001, 'teacher123', 'teacher', None, None),
        (900001, 'admin123', 'admin_sys', None, None),
    ]

    for user_id, password, role, name, group in test_users:
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            password_hash = auth.hash_password(password)
            cursor.execute(
                'INSERT INTO users (user_id, password_hash, role) VALUES (?, ?, ?)',
                (user_id, password_hash, role)
            )
            if role == 'student':
                cursor.execute(
                    'INSERT INTO student_assignments (student_id, student_name, experiment_group) VALUES (?, ?, ?)',
                    (user_id, name, group)
                )

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_database()
    create_default_accounts()
    print("数据库初始化完成")

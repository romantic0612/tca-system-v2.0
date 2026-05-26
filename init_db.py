# -*- coding: utf-8 -*-
"""
数据库初始化独立脚本
"""

import sqlite3
import os
import hashlib
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / 'data' / 'tca_system.db'


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库表结构"""
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
    
    conn.commit()
    conn.close()

def create_default_accounts():
    """创建进入系统所需的最小管理员账号"""
    conn = get_connection()
    cursor = conn.cursor()

    accounts = [
        (900001, 'admin123', 'admin_sys'),
    ]

    for user_id, password, role in accounts:
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            cursor.execute(
                'INSERT INTO users (user_id, password_hash, role) VALUES (?, ?, ?)',
                (user_id, hash_password(password), role)
            )

    conn.commit()
    conn.close()


def create_test_users():
    """显式创建演示/测试用户；生产初始化不调用。"""
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
            cursor.execute(
                'INSERT INTO users (user_id, password_hash, role) VALUES (?, ?, ?)',
                (user_id, hash_password(password), role)
            )
            if role == 'student':
                cursor.execute(
                    'INSERT INTO student_assignments (student_id, student_name, experiment_group) VALUES (?, ?, ?)',
                    (user_id, name, group)
                )

    conn.commit()
    conn.close()

def init_student_states():
    """为学生初始化状态"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT student_id FROM student_assignments')
    students = cursor.fetchall()
    
    for student in students:
        student_id = student[0]
        try:
            cursor.execute('''
                INSERT INTO student_states (student_id, current_agent, error_streak, 
                                           consecutive_correct, total_interactions, 
                                           last_response_time, updated_at)
                VALUES (?, 'Guide', 0, 0, 0, ?, ?)
            ''', (student_id, datetime.now().isoformat(), datetime.now().isoformat()))
        except:
            pass
    
    conn.commit()
    conn.close()
    
    return len(students)

if __name__ == '__main__':
    print("=" * 60)
    print("TCA-System V2.0 数据库初始化")
    print("=" * 60)
    print()
    
    print("[步骤1] 创建数据库表...")
    init_database()
    print("✅ 数据库表创建完成")
    print()
    
    print("[步骤2] 创建默认管理员...")
    create_default_accounts()
    print("✅ 默认管理员创建完成")
    print()
    
    print("[步骤3] 初始化学生状态...")
    count = init_student_states()
    print(f"✅ 为 {count} 个学生初始化状态完成")
    print()
    
    print("[步骤4] 验证结果...")
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"数据表数量: {len(tables)}")
    print("数据表列表:")
    for table in tables:
        print(f"  - {table}")
    
    print()
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    print(f"用户数量: {user_count}")
    
    cursor.execute('SELECT COUNT(*) FROM student_assignments')
    student_count = cursor.fetchone()[0]
    print(f"学生数量: {student_count}")
    
    cursor.execute('SELECT COUNT(*) FROM student_states')
    state_count = cursor.fetchone()[0]
    print(f"学生状态数量: {state_count}")
    
    conn.close()
    
    print()
    print("=" * 60)
    print("✅ 数据库初始化完成！")
    print("=" * 60)

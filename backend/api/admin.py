# -*- coding: utf-8 -*-
"""
TCA-System V2.0 管理端API
========================

管理后台所需数据均从SQLite读取，避免前端硬编码演示数据。
"""

import csv
import io
import sys
import os
import random
from datetime import datetime

from flask import Blueprint, Response, jsonify, request, session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.auth.auth_manager import AuthManager
from backend.core.database.schema import get_connection

admin_bp = Blueprint('admin', __name__)

VALID_GROUPS = ['SA', 'EXP', 'TCA', 'AI-AUTO']


def require_admin():
    role = session.get('role')
    return role in ['admin_exp', 'admin_sys']


def forbidden():
    return jsonify({'success': False, 'error': '权限不足'}), 403


def parse_optional_score(value):
    if value in [None, '']:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        raise ValueError('前测成绩必须是数字')
    if score < 0 or score > 100:
        raise ValueError('前测成绩必须在 0-100 之间')
    return score


def normalize_group(value, default=None):
    group = (value or '').strip().upper()
    if group in ['', '不指定', '未分配', 'NONE', 'NULL']:
        return default
    if group not in VALID_GROUPS:
        raise ValueError('组别不合法')
    return group


def student_row_to_dict(row):
    return {
        'student_id': row['student_id'],
        'name': row['student_name'],
        'class_id': row['class_id'],
        'pretest_score': row['pretest_score'],
        'experiment_group': row['experiment_group'],
        'current_question': row['current_question'] or 1,
        'total_questions': row['total_questions'] or 9,
        'status': '已分配' if row['experiment_group'] else '待分配',
    }


@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    if not require_admin():
        return forbidden()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT student_id, student_name, class_id, pretest_score, experiment_group,
               current_question, total_questions
        FROM student_assignments
        ORDER BY student_id
    ''')
    students = [student_row_to_dict(row) for row in cursor.fetchall()]

    cursor.execute('SELECT user_id, role, created_at FROM users ORDER BY user_id')
    users = [
        {
            'user_id': row['user_id'],
            'role': row['role'],
            'created_at': row['created_at'],
            'status': '正常',
        }
        for row in cursor.fetchall()
    ]

    cursor.execute('''
        SELECT created_at, teacher_id AS actor, intervention_type AS action_type,
               '教师干预: ' || COALESCE(content, '') AS detail
        FROM teacher_overrides
        WHERE teacher_id != 0
        ORDER BY created_at DESC
        LIMIT 30
    ''')
    override_logs = [dict(row) for row in cursor.fetchall()]

    cursor.execute('''
        SELECT created_at, student_id AS actor, 'Agent切换' AS action_type,
               COALESCE(from_agent, '-') || ' -> ' || COALESCE(to_agent, '-') ||
               ' (' || COALESCE(triggered_by, '-') || ')' AS detail
        FROM agent_switches
        ORDER BY created_at DESC
        LIMIT 30
    ''')
    switch_logs = [dict(row) for row in cursor.fetchall()]

    logs = sorted(
        override_logs + switch_logs,
        key=lambda item: item.get('created_at') or '',
        reverse=True,
    )[:30]

    conn.close()

    stats = {'SA': 0, 'EXP': 0, 'TCA': 0, 'AI-AUTO': 0}
    for student in students:
        group = student['experiment_group']
        if group in stats:
            stats[group] += 1

    return jsonify({
        'success': True,
        'students': students,
        'users': users,
        'stats': stats,
        'logs': logs,
    })


@admin_bp.route('/students', methods=['POST'])
def create_student():
    if not require_admin():
        return forbidden()

    data = request.get_json() or {}
    try:
        student_id = int(data.get('student_id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '学号必须是数字'}), 400

    name = (data.get('name') or '').strip()
    class_id = (data.get('class_id') or '').strip()
    try:
        group = normalize_group(data.get('experiment_group'), default=None)
        pretest_score = parse_optional_score(data.get('pretest_score'))
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400
    password = data.get('password') or '123456'

    if not name:
        return jsonify({'success': False, 'error': '姓名不能为空'}), 400

    auth = AuthManager()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (student_id,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '学号已存在'}), 409

    cursor.execute(
        'INSERT INTO users (user_id, password_hash, role, created_at) VALUES (?, ?, "student", ?)',
        (student_id, auth.hash_password(password), datetime.now().isoformat()),
    )
    cursor.execute('''
        INSERT INTO student_assignments
        (student_id, student_name, class_id, pretest_score, experiment_group, current_question, total_questions)
        VALUES (?, ?, ?, ?, ?, 1, 9)
    ''', (student_id, name, class_id, pretest_score, group))
    cursor.execute(
        'INSERT OR IGNORE INTO student_states (student_id, current_agent, updated_at) VALUES (?, "Guide", ?)',
        (student_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'student_id': student_id})


@admin_bp.route('/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    if not require_admin():
        return forbidden()

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    class_id = (data.get('class_id') or '').strip()
    try:
        pretest_score = parse_optional_score(data.get('pretest_score'))
        group = normalize_group(data.get('experiment_group'), default=None)
    except ValueError as exc:
        return jsonify({'success': False, 'error': str(exc)}), 400

    if not name:
        return jsonify({'success': False, 'error': '姓名不能为空'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT student_id FROM student_assignments WHERE student_id = ?', (student_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '学生不存在'}), 404

    cursor.execute('''
        UPDATE student_assignments
        SET student_name = ?, class_id = ?, pretest_score = ?, experiment_group = ?
        WHERE student_id = ?
    ''', (name, class_id, pretest_score, group, student_id))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'student_id': student_id})


@admin_bp.route('/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    if not require_admin():
        return forbidden()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT student_id FROM student_assignments WHERE student_id = ?', (student_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '学生不存在'}), 404

    for table in [
        'student_progress', 'chat_messages', 'teacher_overrides',
        'student_states', 'trigger_events', 'evaluation_records', 'agent_switches'
    ]:
        cursor.execute(f'DELETE FROM {table} WHERE student_id = ?', (student_id,))
    cursor.execute('DELETE FROM student_assignments WHERE student_id = ?', (student_id,))
    cursor.execute('DELETE FROM users WHERE user_id = ? AND role = "student"', (student_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'student_id': student_id})


@admin_bp.route('/students/import', methods=['POST'])
def import_students():
    if not require_admin():
        return forbidden()

    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'error': '请选择CSV文件'}), 400
    filename = (file.filename or '').lower()
    if not filename.endswith('.csv'):
        return jsonify({'success': False, 'error': '当前版本支持CSV导入，Excel请先另存为CSV'}), 400

    try:
        text = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return jsonify({'success': False, 'error': 'CSV请使用UTF-8编码'}), 400

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return jsonify({'success': False, 'error': 'CSV没有可导入的数据'}), 400

    def pick(row, *names):
        for name in names:
            if name in row:
                return row.get(name)
        return None

    auth = AuthManager()
    conn = get_connection()
    cursor = conn.cursor()
    created = 0
    updated = 0
    errors = []
    seen_ids = set()

    for index, row in enumerate(rows, start=2):
        try:
            raw_id = pick(row, '学号', 'student_id', '账号')
            raw_id_text = str(raw_id or '').strip()
            if not raw_id_text.isdigit():
                raise ValueError('学号必须是纯数字')
            if len(raw_id_text) < 6 or len(raw_id_text) > 12:
                raise ValueError('学号长度应为 6-12 位数字')
            student_id = int(raw_id_text)
            if student_id in seen_ids:
                raise ValueError('CSV中存在重复学号')
            seen_ids.add(student_id)
            name = (pick(row, '姓名', 'student_name', 'name') or '').strip()
            if not name:
                raise ValueError('姓名不能为空')
            class_id = (pick(row, '班级', 'class_id', 'class') or '').strip()
            pretest_score = parse_optional_score(pick(row, '前测成绩', 'pretest_score', 'score'))
            group = normalize_group(pick(row, '组别', 'experiment_group', 'group'), default=None)
            password = (pick(row, '密码', 'password') or '123456').strip() or '123456'
        except Exception as exc:
            errors.append({'row': index, 'error': str(exc)})
            continue

        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (student_id,))
        user_exists = cursor.fetchone()
        if not user_exists:
            cursor.execute(
                'INSERT INTO users (user_id, password_hash, role, created_at) VALUES (?, ?, "student", ?)',
                (student_id, auth.hash_password(password), datetime.now().isoformat()),
            )

        cursor.execute('SELECT student_id FROM student_assignments WHERE student_id = ?', (student_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE student_assignments
                SET student_name = ?, class_id = ?, pretest_score = ?, experiment_group = ?
                WHERE student_id = ?
            ''', (name, class_id, pretest_score, group, student_id))
            updated += 1
        else:
            cursor.execute('''
                INSERT INTO student_assignments
                (student_id, student_name, class_id, pretest_score, experiment_group, current_question, total_questions)
                VALUES (?, ?, ?, ?, ?, 1, 9)
            ''', (student_id, name, class_id, pretest_score, group))
            cursor.execute(
                'INSERT OR IGNORE INTO student_states (student_id, current_agent, updated_at) VALUES (?, "Guide", ?)',
                (student_id, datetime.now().isoformat()),
            )
            created += 1

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'success_count': created + updated,
        'failed_count': len(errors),
        'created': created,
        'updated': updated,
        'failed': len(errors),
        'errors': errors[:20],
    })


def shuffled(items, seed=None):
    items = list(items)
    rng = random.Random(seed) if seed is not None else random.Random()
    rng.shuffle(items)
    return items


def assign_groups(students, method, seed=None):
    groups = ['SA', 'EXP', 'TCA', 'AI-AUTO']
    result = {}
    group_index = 0

    def assign_list(student_list):
        nonlocal group_index
        ordered = shuffled(student_list, seed)
        for student in ordered:
            result[student['student_id']] = groups[group_index % len(groups)]
            group_index += 1

    if method == 'block':
        by_class = {}
        for student in students:
            by_class.setdefault(student['class_id'] or '未知', []).append(student)
        for class_id in sorted(by_class):
            assign_list(by_class[class_id])
    elif method == 'stratified':
        with_scores = [s for s in students if s['pretest_score'] is not None]
        without_scores = [s for s in students if s['pretest_score'] is None]
        if with_scores:
            ordered = sorted(with_scores, key=lambda s: s['pretest_score'])
            buckets = [ordered[i::3] for i in range(3)]
            for bucket in buckets:
                assign_list(bucket)
            if without_scores:
                assign_list(without_scores)
        else:
            assign_list(students)
    else:
        assign_list(students)

    return result


@admin_bp.route('/students/assignments', methods=['POST'])
def bulk_assign_students():
    if not require_admin():
        return forbidden()

    data = request.get_json() or {}
    method = data.get('method') or 'simple'
    if method not in ['simple', 'block', 'stratified']:
        return jsonify({'success': False, 'error': '分组方法不合法'}), 400
    seed = data.get('seed')
    try:
        seed = int(seed) if seed not in [None, ''] else None
    except ValueError:
        return jsonify({'success': False, 'error': '随机种子必须是数字'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT student_id, class_id, pretest_score
        FROM student_assignments
        ORDER BY student_id
    ''')
    students = [dict(row) for row in cursor.fetchall()]
    if not students:
        conn.close()
        return jsonify({'success': False, 'error': '没有学生可分组'}), 400

    assignments = assign_groups(students, method, seed)
    for student_id, group in assignments.items():
        cursor.execute(
            'UPDATE student_assignments SET experiment_group = ? WHERE student_id = ?',
            (group, student_id),
        )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'updated': len(assignments)})


@admin_bp.route('/students/assignments/clear', methods=['POST'])
def clear_student_assignments():
    if not require_admin():
        return forbidden()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE student_assignments SET experiment_group = NULL')
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'updated': updated})


@admin_bp.route('/teachers', methods=['POST'])
def create_teacher():
    if not require_admin():
        return forbidden()

    data = request.get_json() or {}
    try:
        user_id = int(data.get('user_id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '工号必须是数字'}), 400

    role = data.get('role') or 'teacher'
    password = data.get('password') or 'teacher123'
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '角色不合法'}), 400

    auth = AuthManager()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '账号已存在'}), 409

    cursor.execute(
        'INSERT INTO users (user_id, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
        (user_id, auth.hash_password(password), role, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'user_id': user_id})


@admin_bp.route('/export/assignments.csv', methods=['GET'])
def export_assignments_csv():
    if not require_admin():
        return forbidden()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT student_id, student_name, class_id, pretest_score, experiment_group,
               current_question, total_questions
        FROM student_assignments
        ORDER BY student_id
    ''')
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['学号', '姓名', '班级', '前测成绩', '组别', '当前题号', '总题数'])
    for row in rows:
        writer.writerow([
            row['student_id'], row['student_name'], row['class_id'],
            row['pretest_score'], row['experiment_group'], row['current_question'], row['total_questions'],
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=assignments.csv'},
    )


@admin_bp.route('/export/experiment-data.csv', methods=['GET'])
def export_experiment_data_csv():
    if not require_admin():
        return forbidden()

    conn = get_connection()
    cursor = conn.cursor()

    sections = []

    def add_section(title, headers, sql):
        cursor.execute(sql)
        rows = cursor.fetchall()
        sections.append((title, headers, rows))

    add_section(
        'students',
        ['student_id', 'student_name', 'class_id', 'pretest_score', 'experiment_group', 'current_question', 'total_questions'],
        '''
        SELECT student_id, student_name, class_id, pretest_score, experiment_group,
               current_question, total_questions
        FROM student_assignments
        ORDER BY student_id
        ''',
    )
    add_section(
        'chat_messages',
        ['id', 'student_id', 'agent_name', 'message_type', 'content', 'question_id', 'override_id', 'created_at'],
        '''
        SELECT id, student_id, agent_name, message_type, content, question_id, override_id, created_at
        FROM chat_messages
        ORDER BY created_at, id
        ''',
    )
    add_section(
        'evaluation_records',
        ['id', 'student_id', 'question_id', 'student_answer', 'standard_answer', 'is_correct', 'error_type', 'score', 'confidence', 'key_mistake', 'suggestion', 'evaluated_at'],
        '''
        SELECT id, student_id, question_id, student_answer, standard_answer, is_correct,
               error_type, score, confidence, key_mistake, suggestion, evaluated_at
        FROM evaluation_records
        ORDER BY evaluated_at, id
        ''',
    )
    add_section(
        'trigger_events',
        ['id', 'student_id', 'trigger_level', 'error_type', 'error_streak_value', 'stagnation_seconds', 'detected_keywords', 'trigger_strength', 'diagnosis_result', 'created_at'],
        '''
        SELECT id, student_id, trigger_level, error_type, error_streak_value,
               stagnation_seconds, detected_keywords, trigger_strength, diagnosis_result, created_at
        FROM trigger_events
        ORDER BY created_at, id
        ''',
    )
    add_section(
        'teacher_overrides',
        ['id', 'student_id', 'teacher_id', 'override_type', 'intervention_type', 'content', 'question_id', 'trigger_event_id', 'status', 'created_at'],
        '''
        SELECT id, student_id, teacher_id, override_type, intervention_type, content,
               question_id, trigger_event_id, status, created_at
        FROM teacher_overrides
        ORDER BY created_at, id
        ''',
    )

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    for index, (title, headers, rows) in enumerate(sections):
        if index:
            writer.writerow([])
        writer.writerow([f'[{title}]'])
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row[header] for header in headers])

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename=experiment-data.csv'},
    )

# -*- coding: utf-8 -*-
"""
TCA-System V2.0 教师API
======================

教师干预相关API接口
"""

from flask import Blueprint, request, jsonify, session
import json
import sqlite3
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database.schema import get_connection

teacher_bp = Blueprint('teacher', __name__)

QUESTION_BANK = {
    1: {'text': '解方程：3(x-2)+1=x-(2x-1)', 'knowledge_point': '一元一次方程'},
    2: {'text': '解方程：2(x-1)=3x+5', 'knowledge_point': '一元一次方程'},
    3: {'text': '解方程：2x-6=-3x+9', 'knowledge_point': '一元一次方程'},
    4: {'text': '学校要购入两种记录本，预计花费460元，其中A种记录本每本3元，B种记录本每本2元，且购买A种记录本的数量比B种记录本的2倍还多20本。(1)求购买A和B两种记录本的数量；(2)某商店搞促销活动，A种记录本按8折销售，B种记录本按9折销售，则学校此次可以节省多少钱?', 'knowledge_point': '一元一次方程应用'},
    5: {'text': '一项工程需要甲、乙两队完成，已知甲队单独完成需要48天，乙队单独完成需要60天。甲队先做12天，然后甲、乙两队合作完成剩下的工作。(1)甲、乙两队合作还需要多少天完成此项工作?(2)已知甲队每天的劳务费比乙队多30元，完成这项工程共需支付劳务费7200元。则甲、乙两队每天的劳务费各是多少元?', 'knowledge_point': '工程问题'},
    6: {'text': '某工厂现有30m2木料，准备制作各种尺寸的方桌与凳子。如果1m2木料可制作40个方桌或制作80个凳子。A类型套桌由一个方桌和四个凳子组成，每套售价2000元，B类型套桌由一个方桌和八个凳子组成，每套售价3500元。(1)若用全部木料生产A类型套桌，且桌子、凳子恰好配套，问全部卖出可以卖多少钱?(2)若用全部木料生产A、B两种类型套桌，且桌子、凳子恰好配套，全部卖出，卖了824000元。问制作了多少套A类型套桌?', 'knowledge_point': '配套问题'},
    7: {'text': '某家具厂现有10立方米木材，准备用来制作方桌，其中用部分木材制作桌面，其余木材制作桌腿。已知制作一张方桌需要1张桌面和4条桌腿，1立方米木材可制作50张桌面或300条桌腿，要使制作出的桌面、桌腿恰好配套。(1)求制作桌面的木材和制作桌腿的木材分别为多少立方米?(2)若该家具厂的木材进货价为每立方米1500元，制成方桌后，每张方桌的售价为150元，则该家具厂制作的这批方桌全部售出后共获利多少元?', 'knowledge_point': '配套问题与利润'},
    8: {'text': '哈佳高铁建设工程中，有一路段由甲、乙两个工程队负责完成。甲工程队单独完成此项工程需60天，比乙工程队单独完成此项工程多用30天，若甲先施工6天，再由甲、乙合作完成剩余工程。(1)甲、乙还需要合作多少天完成?(2)如果甲工程队每天需工程费500元，乙工程队每天需工程费700元，若甲队先单独工作若干天再由乙工程队完成剩余的任务，支付工程队总费用24000元，求甲队工作的天数。', 'knowledge_point': '工程问题'},
    9: {'text': '某学校准备请甲、乙两人搬运一批图书，已知甲单独运完需要10天，乙单独运完需要20天。甲先搬运了4天，然后甲、乙两人合作运完剩下的图书。(1)甲、乙两人合作还需要多少天运完图书?(2)已知甲每天的薪酬比乙多50元，运完图书后学校共需支付薪酬2800元。则甲、乙两人每天的薪酬分别为多少元?', 'knowledge_point': '工程问题'},
}


def get_question_info(question_id):
    question_id = int(question_id or 1)
    info = QUESTION_BANK.get(question_id, {'text': '请完成当前题目。', 'knowledge_point': '待补充'})
    return {
        'question_id': question_id,
        'text': info['text'],
        'knowledge_point': info['knowledge_point'],
    }


@teacher_bp.route('/intervene', methods=['POST'])
def intervene():
    """
    教师发送干预
    
    请求体：
    {
        "student_id": 20240001,
        "target_agent": "Guide",
        "content": "注意已知条件中两个角的关系"
    }
    
    响应：
    {
        "success": true,
        "override_id": 1
    }
    """
    # 权限检查
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    role = session['role']
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403
    
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        target_agent = data.get('target_agent', 'Guide')
        content = data.get('content', '')
        intervention_type = data.get('intervention_type', 'manual_override')
        trigger_event_id = data.get('trigger_event_id')
        diagnosis_context = data.get('diagnosis_context', {})
        question_id = data.get('question_id')
        
        if not student_id or not content:
            return jsonify({'success': False, 'error': '参数不完整'}), 400
        
        teacher_id = session['user_id']
        
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT student_name, experiment_group FROM student_assignments WHERE student_id = ?',
            (student_id,),
        )
        assignment = cursor.fetchone()
        if not assignment:
            conn.close()
            return jsonify({'success': False, 'error': '学生不存在'}), 404
        if assignment['experiment_group'] != 'TCA':
            conn.close()
            return jsonify({
                'success': False,
                'error': '非TCA组仅可观察，不允许教师干预',
            }), 403
        
        cursor.execute(
            'SELECT current_agent FROM student_states WHERE student_id = ?',
            (student_id,)
        )
        state_row = cursor.fetchone()
        from_agent = state_row[0] if state_row else 'Guide'

        # 写入教师干预表
        cursor.execute('''
            INSERT INTO teacher_overrides 
            (student_id, teacher_id, override_type, content, question_id, created_at, status,
             intervention_type, diagnosis_context, trigger_event_id)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
        ''', (
            student_id,
            teacher_id,
            target_agent,
            content,
            question_id,
            datetime.now().isoformat(),
            intervention_type,
            json.dumps(diagnosis_context, ensure_ascii=False),
            trigger_event_id,
        ))
        
        override_id = cursor.lastrowid

        cursor.execute(
            'INSERT OR IGNORE INTO student_states (student_id, current_agent, updated_at) VALUES (?, ?, ?)',
            (student_id, 'Guide', datetime.now().isoformat())
        )
        cursor.execute(
            'UPDATE student_states SET current_agent = ?, updated_at = ? WHERE student_id = ?',
            (target_agent, datetime.now().isoformat(), student_id)
        )
        if target_agent != from_agent:
            cursor.execute('''
                INSERT INTO agent_switches
                (student_id, from_agent, to_agent, switch_reason, triggered_by, trigger_event_id, created_at)
                VALUES (?, ?, ?, ?, 'teacher', ?, ?)
            ''', (
                student_id,
                from_agent,
                target_agent,
                intervention_type,
                trigger_event_id,
                datetime.now().isoformat(),
            ))
        cursor.execute(
            'INSERT INTO chat_messages (student_id, agent_name, message_type, content, question_id, override_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (student_id, f'Teacher-{teacher_id}', 'teacher', content, question_id, override_id, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        
        # WebSocket: 推送教师干预给学生端
        try:
            from backend.websocket.events import get_socketio
            sio = get_socketio()
            sio.emit('teacher_override', {
                'teacher_id': teacher_id,
                'override_id': override_id,
                'override_type': target_agent,
                'intervention_type': intervention_type,
                'content': content,
                'question_id': question_id,
                'target_agent': target_agent,
                'trigger_event_id': trigger_event_id,
                'timestamp': datetime.now().isoformat()
            }, room=f'student_{student_id}')
            
            # 同时推送干预记录到教师房间供其他教师端同步
            sio.emit('student_update', {
                'student_id': student_id,
                'student_name': '',
                'experiment_group': '',
                'current_question': None,
                'action': 'teacher_intervene',
                'data': {
                    'override_type': target_agent,
                    'intervention_type': intervention_type,
                    'content': content
                },
                'timestamp': datetime.now().isoformat()
            }, room='teacher_room')
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'override_id': override_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@teacher_bp.route('/help-request', methods=['POST'])
def help_request():
    """
    学生发起求助
    
    请求体：
    {
        "student_id": 20240001,
        "question_id": 3,
        "content": "老师，我卡住了..."
    }
    
    响应：
    {
        "success": true
    }
    """
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        question_id = data.get('question_id')
        content = data.get('content', '学生请求帮助')
        
        if not student_id:
            return jsonify({'success': False, 'error': '缺少student_id'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # 写入教师干预表（状态为help_request）
        cursor.execute('''
            INSERT INTO teacher_overrides 
            (student_id, teacher_id, override_type, content, question_id, created_at, status)
            VALUES (?, 0, 'help_request', ?, ?, ?, 'help_request')
        ''', (student_id, content, question_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()

        # WebSocket: 推送求助请求给教师端
        try:
            from backend.websocket.events import get_socketio
            sio = get_socketio()
            cursor_name = '未知'
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT student_name FROM student_assignments WHERE student_id = ?', (student_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                cursor_name = row[0]
            sio.emit('help_request', {
                'student_id': student_id,
                'student_name': cursor_name,
                'question_id': question_id,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }, room='teacher_room')
        except Exception:
            pass
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@teacher_bp.route('/help-requests', methods=['GET'])
def get_help_requests():
    """
    教师查看求助列表
    
    响应：
    {
        "success": true,
        "requests": [
            {
                "id": 1,
                "student_id": 20240001,
                "student_name": "张明",
                "question_id": 3,
                "content": "...",
                "created_at": "..."
            }
        ]
    }
    """
    # 权限检查
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    role = session['role']
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 联合查询获取学生姓名
        cursor.execute('''
            SELECT 
                to2.id,
                to2.student_id,
                sa.student_name,
                to2.question_id,
                to2.content,
                to2.created_at,
                to2.trigger_event_id
            FROM teacher_overrides to2
            LEFT JOIN student_assignments sa ON to2.student_id = sa.student_id
            WHERE to2.status = 'help_request'
            ORDER BY to2.created_at DESC
            LIMIT 50
        ''')
        
        requests = []
        for row in cursor.fetchall():
            requests.append({
                'id': row[0],
                'student_id': row[1],
                'student_name': row[2] or '未知',
                'question_id': row[3],
                'content': row[4],
                'created_at': row[5],
                'trigger_event_id': row[6]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'requests': requests
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@teacher_bp.route('/event-detail', methods=['GET'])
def get_event_detail():
    """获取教师端待处理事件详情，用于右侧详情面板。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401

    role = session['role']
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403

    student_id = request.args.get('student_id', type=int)
    question_id = request.args.get('question_id', type=int)
    trigger_event_id = request.args.get('trigger_event_id', type=int)

    if not student_id:
        return jsonify({'success': False, 'error': '缺少student_id'}), 400

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sa.student_id, sa.student_name, sa.experiment_group,
                   sa.current_question, sa.total_questions,
                   COALESCE(ss.current_agent, 'Guide') AS current_agent,
                   COALESCE(ss.error_streak, 0) AS error_streak,
                   ss.last_error_type,
                   ss.last_trigger_level
            FROM student_assignments sa
            LEFT JOIN student_states ss ON sa.student_id = ss.student_id
            WHERE sa.student_id = ?
        ''', (student_id,))
        student = cursor.fetchone()
        if not student:
            conn.close()
            return jsonify({'success': False, 'error': '学生不存在'}), 404

        active_question = question_id or student['current_question'] or 1

        cursor.execute('''
            SELECT question_id, score, error_type, key_mistake, suggestion,
                   is_correct, evaluated_at
            FROM evaluation_records
            WHERE student_id = ? AND question_id = ?
            ORDER BY evaluated_at DESC
            LIMIT 1
        ''', (student_id, active_question))
        evaluation = cursor.fetchone()

        trigger = None
        if trigger_event_id:
            cursor.execute('SELECT * FROM trigger_events WHERE id = ?', (trigger_event_id,))
            trigger = cursor.fetchone()
        if not trigger:
            cursor.execute('''
                SELECT * FROM trigger_events
                WHERE student_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (student_id,))
            trigger = cursor.fetchone()

        cursor.execute('''
            SELECT agent_name, message_type, content, created_at, question_id, override_id
            FROM chat_messages
            WHERE student_id = ? AND question_id = ?
            ORDER BY created_at ASC
            LIMIT 50
        ''', (student_id, active_question))
        rows = cursor.fetchall()
        message_question_id = active_question

        messages = [
            {
                'agent': row['agent_name'],
                'type': row['message_type'],
                'content': row['content'],
                'time': row['created_at'],
                'question_id': row['question_id'],
                'override_id': row['override_id'],
            }
            for row in rows
        ]

        cursor.execute('''
            SELECT id, teacher_id, override_type, intervention_type, content,
                   question_id, created_at, status, trigger_event_id, feedback, feedback_at
            FROM teacher_overrides
            WHERE student_id = ?
              AND teacher_id != 0
              AND question_id = ?
            ORDER BY created_at ASC
        ''', (student_id, active_question))
        overrides = [dict(row) for row in cursor.fetchall()]

        conn.close()

        diagnosis = None
        if trigger and trigger['diagnosis_result']:
            try:
                diagnosis = json.loads(trigger['diagnosis_result'])
            except Exception:
                diagnosis = trigger['diagnosis_result']

        return jsonify({
            'success': True,
            'student': {
                'student_id': student['student_id'],
                'student_name': student['student_name'],
                'experiment_group': student['experiment_group'],
                'current_question': student['current_question'],
                'total_questions': student['total_questions'],
                'current_agent': student['current_agent'],
                'error_streak': student['error_streak'],
                'last_error_type': student['last_error_type'],
                'last_trigger_level': student['last_trigger_level'],
            },
            'question_id': message_question_id,
            'question': get_question_info(message_question_id),
            'evaluation': dict(evaluation) if evaluation else None,
            'trigger': dict(trigger) if trigger else None,
            'diagnosis': diagnosis,
            'messages': messages,
            'overrides': overrides,
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@teacher_bp.route('/help-requests/<int:request_id>/read', methods=['POST'])
def mark_help_request_read(request_id):
    """将单条待处理请求标记为已读/已处理。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401

    role = session['role']
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE teacher_overrides SET status = 'read' WHERE id = ? AND status = 'help_request'",
        (request_id,),
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'updated': updated})


@teacher_bp.route('/help-requests/read-all', methods=['POST'])
def mark_all_help_requests_read():
    """将当前待处理请求全部标记为已读。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401

    role = session['role']
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE teacher_overrides SET status = 'read' WHERE status = 'help_request'")
    updated = cursor.rowcount
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'updated': updated})

# -*- coding: utf-8 -*-
"""
TCA-System V2.0 学生API
======================

学生相关API接口，包括：
- 获取进度
- 提交答案
- 聊天交互
"""

from flask import Blueprint, request, jsonify, session
import json
import re
import sqlite3
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database.schema import get_connection
from backend.core.intelligence import (
    RuleEvaluator,
    apply_group_strategy,
    detect_trigger,
    ensure_student_state,
    get_student_profile,
    record_evaluation,
    record_trigger,
    update_error_state,
)
from backend.core.llm_client import evaluate_answer_with_llm, generate_agent_reply
from flask_socketio import emit as socket_emit

student_bp = Blueprint('student', __name__)


def json_dumps_safe(value):
    return json.dumps(value or {}, ensure_ascii=False)


def serialize_timestamp(value):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


HELP_INTENT_KEYWORDS = [
    '不会',
    '不懂',
    '不理解',
    '不明白',
    '不知道',
    '没思路',
    '卡住',
    '帮帮我',
    '帮我',
    '教我',
    '怎么做',
    '怎么解',
    '提示',
    '求助',
]

FINAL_ANSWER_PREFIXES = [
    '答案是',
    '答案:',
    '答案：',
    '最终答案',
    '我选',
    '选',
    '我认为答案是',
    '我觉得答案是',
]

THINKING_PREFIXES = [
    '我觉得',
    '我想',
    '是不是',
    '应该是',
    '可能是',
    '大概是',
    '所以是',
]


def classify_message_intent(message):
    compact = re.sub(r'\s+', '', str(message or ''))
    if not compact:
        return 'free_chat'

    if any(mark in compact for mark in ['?', '？', '吗', '呢']):
        return 'guide_interaction'

    if any(keyword in compact for keyword in HELP_INTENT_KEYWORDS):
        return 'help_request'

    if any(compact.startswith(prefix) for prefix in FINAL_ANSWER_PREFIXES):
        return 'final_answer'

    if any(compact.startswith(prefix) for prefix in THINKING_PREFIXES):
        return 'thinking_process'

    if re.fullmatch(r'[A-Da-d]', compact):
        return 'final_answer'
    if re.fullmatch(r'-?\d+(?:\.\d+)?(?:度|°)?', compact):
        return 'final_answer'
    if re.fullmatch(r'[x-zX-Z]\s*=\s*-?\d+(?:\.\d+)?', compact):
        return 'final_answer'
    if re.fullmatch(r'[-+*/=().0-9x-zX-Z]+(?:度|°)?', compact) and re.search(r'\d', compact):
        return 'final_answer'

    return 'free_chat'


def build_teacher_notice(profile, trigger, source, message=''):
    group = profile.get('experiment_group') or '-'
    level = trigger.get('trigger_level') or 'none'
    prefix = '系统检测到学生学习困难'
    if source == 'chat':
        prefix = '系统检测到学生主动求助'
    if group == 'TCA':
        action = '建议教师查看并决定是否干预。'
    else:
        action = f'{group}组按实验规则自动处理，教师端同步留痕观察。'
    suffix = f' 学生消息：{message[:80]}' if message else ''
    return f'{prefix}：{level} 触发；{action}{suffix}'


def build_evaluation_feedback(evaluation, trigger=None, state=None, decision=None):
    if getattr(evaluation, 'skip_evaluation', False):
        return ''
    feedback = 'Evaluator评估：评分 ' + str(evaluation.score) + '/100'
    if evaluation.correct:
        feedback += '，答案正确。'
    else:
        feedback += '，错误类型：' + str(evaluation.error_type)
        if evaluation.key_mistake:
            feedback += '；' + evaluation.key_mistake
        feedback += '。'
    if state and state.get('error_streak') is not None:
        feedback += ' 错误累计：' + str(round(float(state['error_streak'] or 0), 1)) + '。'
    if trigger and trigger.get('triggered'):
        feedback += ' 已触发：' + str(trigger.get('trigger_level')) + '（' + str(trigger.get('trigger_strength')) + '）。'
    if decision and decision.get('switched'):
        feedback += ' 当前模式切换为：' + str(decision.get('agent')) + '。'
    if evaluation.suggestion and not evaluation.correct:
        feedback += ' ' + evaluation.suggestion
    return feedback


@student_bp.route('/progress', methods=['GET'])
def get_progress():
    """
    获取学生学习进度
    
    响应：
    {
        "success": true,
        "current_question": 3,
        "total_questions": 9,
        "experiment_group": "TCA",
        "progress_percent": 30
    }
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    try:
        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT current_question, total_questions, experiment_group FROM student_assignments WHERE student_id = ?',
            (student_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'success': False, 'error': '学生信息不存在'}), 404
        
        current = row[0] or 1
        total = row[1] or 9
        
        return jsonify({
            'success': True,
            'current_question': current,
            'total_questions': total,
            'experiment_group': row[2],
            'progress_percent': int((current / total) * 100)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/submit-answer', methods=['POST'])
def submit_answer():
    """
    提交答案
    
    请求体：
    {
        "question_id": 3,
        "answer": "A",
        "time_spent": 120
    }
    
    响应：
    {
        "success": true,
        "is_correct": true,
        "next_question": 4
    }
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    if session['role'] != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403
    
    try:
        data = request.get_json()
        question_id = data.get('question_id')
        answer = data.get('answer')
        time_spent = data.get('time_spent', 0)
        
        if not question_id or not answer:
            return jsonify({'success': False, 'error': '参数不完整'}), 400
        
        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        
        profile = get_student_profile(cursor, student_id)
        evaluator = RuleEvaluator()
        llm_evaluation = evaluate_answer_with_llm(answer, question_id)
        evaluation = llm_evaluation or evaluator.evaluate(answer, question_id)
        evaluation_source = 'llm' if llm_evaluation else 'rule'
        if getattr(evaluation, 'skip_evaluation', False):
            conn.close()
            return jsonify({
                'success': True,
                'is_correct': False,
                'score': evaluation.score,
                'error_type': evaluation.error_type,
                'confidence': evaluation.confidence,
                'key_mistake': evaluation.key_mistake,
                'suggestion': evaluation.suggestion,
                'standard_answer': evaluation.standard_answer,
                'skip_evaluation': True,
                'evaluation_source': 'skipped',
                'triggered': False,
                'trigger_level': 'none',
                'trigger_strength': 'NONE',
            })
        state = update_error_state(cursor, student_id, profile['experiment_group'], evaluation)
        trigger = detect_trigger(
            state['error_streak'],
            evaluation.error_type,
            message=answer,
            time_spent=time_spent,
            confidence=evaluation.confidence,
        )
        trigger_event_id = record_trigger(
            cursor,
            student_id,
            trigger,
            evaluation.error_type,
            state['error_streak'],
        )
        decision = apply_group_strategy(
            cursor,
            student_id,
            profile['experiment_group'],
            state['current_agent'],
            trigger,
            trigger_event_id,
            state.get('consecutive_correct', 0),
        )
        record_evaluation(cursor, student_id, question_id, answer, evaluation)

        cursor.execute(
            'INSERT INTO student_progress (student_id, question_id, answer, time_spent, created_at) VALUES (?, ?, ?, ?, ?)',
            (student_id, question_id, answer, time_spent, datetime.now().isoformat())
        )

        is_correct = evaluation.correct
        cursor.execute(
            'UPDATE student_progress SET is_correct = ? WHERE id = ?',
            (is_correct, cursor.lastrowid)
        )

        if trigger['triggered']:
            cursor.execute('''
                INSERT INTO teacher_overrides
                (student_id, teacher_id, override_type, content, question_id,
                 created_at, status, intervention_type, diagnosis_context, trigger_event_id)
                VALUES (?, 0, 'system_trigger', ?, ?, ?, 'help_request',
                        'system_trigger', ?, ?)
            ''', (
                student_id,
                build_teacher_notice(profile, trigger, 'answer', answer),
                question_id,
                datetime.now().isoformat(),
                json_dumps_safe(trigger['diagnosis']),
                trigger_event_id,
            ))
        
        cursor.execute(
            'SELECT current_question, total_questions FROM student_assignments WHERE student_id = ?',
            (student_id,)
        )
        row = cursor.fetchone()
        total = row[1] or 9
        next_question = min(int(question_id) + 1, total)
        
        cursor.execute(
            'UPDATE student_assignments SET current_question = ? WHERE student_id = ?',
            (next_question, student_id)
        )
        
        conn.commit()
        conn.close()
        
        # WebSocket: 推送学生状态更新到教师端
        try:
            from backend.websocket.events import get_socketio
            sio = get_socketio()
            sio.emit('student_update', {
                'student_id': student_id,
                'student_name': profile['student_name'],
                'experiment_group': profile['experiment_group'],
                'current_question': next_question,
                'action': 'submit_answer',
                'trigger_event_id': trigger_event_id,
                'data': {
                    'question_id': question_id,
                    'answer': answer,
                    'is_correct': is_correct,
                    'time_spent': time_spent,
                    'score': evaluation.score,
                    'error_type': evaluation.error_type,
                    'skip_evaluation': evaluation.skip_evaluation,
                    'error_streak': state['error_streak'],
                    'trigger': trigger,
                    'agent': decision['agent']
                },
                'timestamp': datetime.now().isoformat()
            }, room='teacher_room')
            if trigger['triggered']:
                sio.emit('help_request', {
                    'student_id': student_id,
                    'student_name': profile['student_name'],
                    'question_id': question_id,
                    'content': build_teacher_notice(profile, trigger, 'answer', answer),
                    'trigger_event_id': trigger_event_id,
                    'timestamp': datetime.now().isoformat()
                }, room='teacher_room')
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'is_correct': is_correct,
            'next_question': next_question,
            'score': evaluation.score,
            'error_type': evaluation.error_type,
            'confidence': evaluation.confidence,
            'key_mistake': evaluation.key_mistake,
            'suggestion': evaluation.suggestion,
            'standard_answer': evaluation.standard_answer,
            'skip_evaluation': evaluation.skip_evaluation,
            'evaluation_source': evaluation_source,
            'error_streak': state['error_streak'],
            'triggered': trigger['triggered'],
            'trigger_level': trigger['trigger_level'],
            'trigger_strength': trigger['trigger_strength'],
            'current_agent': decision['agent'],
            'agent': decision['agent'],
            'switched': decision['switched'],
            'explanation': decision['explanation'],
            'teacher_alert': decision['teacher_alert'],
            'mode_note': decision['mode_note']
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/chat', methods=['POST'])
def chat():
    """
    学生聊天交互
    
    请求体：
    {
        "message": "这道题怎么做？",
        "question_id": 3,
        "agent": "Guide"
    }
    
    响应：
    {
        "success": true,
        "response": "让我们来分析一下这道题...",
        "agent": "Guide"
    }
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    
    if session['role'] != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403
    
    try:
        data = request.get_json()
        message = data.get('message')
        question_id = data.get('question_id')
        agent = data.get('agent', 'Guide')
        
        if not message:
            return jsonify({'success': False, 'error': '消息不能为空'}), 400
        
        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        
        profile = get_student_profile(cursor, student_id)
        state_row = ensure_student_state(cursor, student_id)
        message_intent = classify_message_intent(message)
        awaiting_final_answer = message_intent != 'final_answer'
        evaluation = evaluate_answer_with_llm(message, question_id) if question_id and message_intent == 'final_answer' else None
        evaluation_source = (
            'skipped_intent'
            if message_intent != 'final_answer'
            else ('skipped' if evaluation and getattr(evaluation, 'skip_evaluation', False) else ('llm' if evaluation else None))
        )
        evaluation_feedback = ''
        next_question = None

        if evaluation and not getattr(evaluation, 'skip_evaluation', False):
            state = update_error_state(cursor, student_id, profile['experiment_group'], evaluation)
            trigger = detect_trigger(
                state['error_streak'],
                evaluation.error_type,
                message=message,
                time_spent=0,
                confidence=evaluation.confidence,
            )
            trigger_error_type = evaluation.error_type
            trigger_error_streak = state['error_streak']
            current_agent_for_strategy = state['current_agent']
            consecutive_correct = state.get('consecutive_correct', 0)
        else:
            trigger = detect_trigger(
                state_row['error_streak'] or 0,
                state_row['last_error_type'] or 'none',
                message=message,
                time_spent=0,
            )
            trigger_error_type = state_row['last_error_type'] or 'none'
            trigger_error_streak = state_row['error_streak'] or 0
            current_agent_for_strategy = state_row['current_agent'] or agent
            consecutive_correct = state_row['consecutive_correct'] or 0

        trigger_event_id = record_trigger(
            cursor,
            student_id,
            trigger,
            trigger_error_type,
            trigger_error_streak,
        )
        decision = apply_group_strategy(
            cursor,
            student_id,
            profile['experiment_group'],
            current_agent_for_strategy,
            trigger,
            trigger_event_id,
            consecutive_correct,
        )
        agent = decision['agent']

        cursor.execute(
            'INSERT INTO chat_messages (student_id, agent_name, message_type, content, question_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            (student_id, agent, 'user', message, question_id, datetime.now().isoformat())
        )

        if evaluation and not getattr(evaluation, 'skip_evaluation', False):
            record_evaluation(cursor, student_id, question_id, message, evaluation)
            cursor.execute(
                'INSERT INTO student_progress (student_id, question_id, answer, time_spent, created_at) VALUES (?, ?, ?, ?, ?)',
                (student_id, question_id, message, 0, datetime.now().isoformat())
            )
            cursor.execute(
                'UPDATE student_progress SET is_correct = ? WHERE id = ?',
                (evaluation.correct, cursor.lastrowid)
            )
            cursor.execute(
                'SELECT current_question, total_questions FROM student_assignments WHERE student_id = ?',
                (student_id,)
            )
            row = cursor.fetchone()
            if row:
                total = row['total_questions'] if hasattr(row, 'keys') else row[1]
                next_question = min(int(question_id) + 1, total or 9)
                cursor.execute(
                    'UPDATE student_assignments SET current_question = ? WHERE student_id = ?',
                    (next_question, student_id)
                )
            evaluation_feedback = build_evaluation_feedback(evaluation, trigger, state, decision)
            if evaluation_feedback:
                cursor.execute(
                    'INSERT INTO chat_messages (student_id, agent_name, message_type, content, question_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (student_id, 'Evaluator', 'system', evaluation_feedback, question_id, datetime.now().isoformat())
                )

        if trigger['triggered']:
            cursor.execute('''
                INSERT INTO teacher_overrides
                (student_id, teacher_id, override_type, content, question_id,
                 created_at, status, intervention_type, diagnosis_context, trigger_event_id)
                VALUES (?, 0, 'system_trigger', ?, ?, ?, 'help_request',
                        'system_trigger', ?, ?)
            ''', (
                student_id,
                build_teacher_notice(profile, trigger, 'answer' if evaluation and not getattr(evaluation, 'skip_evaluation', False) else 'chat', message),
                question_id,
                datetime.now().isoformat(),
                json_dumps_safe(trigger['diagnosis']),
                trigger_event_id,
            ))

        cursor.execute('''
            SELECT agent_name, message_type, content, created_at
            FROM chat_messages
            WHERE student_id = ? AND (? IS NULL OR question_id = ?)
            ORDER BY created_at DESC
            LIMIT 6
        ''', (student_id, question_id, question_id))
        history = [
            {
                'agent': row['agent_name'],
                'type': row['message_type'],
                'content': row['content'],
                'time': row['created_at'],
            }
            for row in reversed(cursor.fetchall())
        ]
        
        conn.commit()
        conn.close()
        
        evaluated_as_answer = evaluation and not getattr(evaluation, 'skip_evaluation', False)
        if evaluated_as_answer:
            response_text = evaluation_feedback or build_evaluation_feedback(evaluation, trigger, state, decision)
            response_source = 'evaluator'
        else:
            response_text = generate_agent_reply(
                agent,
                profile['experiment_group'],
                question_id,
                message,
                history=history,
                decision=decision,
            )
            response_source = 'llm' if response_text else 'template'
            if not response_text and agent == 'Tutor':
                response_text = f"【Tutor】我来给你更直接的分步提示：先找已知条件，再写出公式，最后代入计算。你刚才的问题是：{message[:50]}"
            elif not response_text:
                response_text = f"【{agent}】收到你的问题：{message[:50]}... 我们先从题目条件入手，一步步分析。"
            if decision['explanation']:
                response_text = decision['explanation'] + "\n\n" + response_text

            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO chat_messages (student_id, agent_name, message_type, content, question_id, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                    (student_id, agent, 'assistant', response_text, question_id, datetime.now().isoformat())
                )
                conn.commit()
                conn.close()
            except Exception:
                pass
        
        # WebSocket: 推送智能体回复给学生
        try:
            from backend.websocket.events import get_socketio
            sio = get_socketio()
            response_agent = 'Evaluator' if evaluated_as_answer else agent
            response_message_type = 'system' if evaluated_as_answer else 'assistant'
            sio.emit('agent_response', {
                'agent_name': response_agent,
                'message_type': response_message_type,
                'response': response_text,
                'response_source': response_source,
                'evaluation': evaluation.to_dict() if evaluation else None,
                'question_id': question_id,
                'timestamp': datetime.now().isoformat()
            }, room=f'student_{student_id}')
            
            # 同时推送学生聊天状态更新给教师端
            sio.emit('student_update', {
                'student_id': student_id,
                'student_name': profile['student_name'],
                'experiment_group': profile['experiment_group'],
                'current_question': profile['current_question'],
                'action': 'chat',
                'trigger_event_id': trigger_event_id,
                'data': {
                    'question_id': question_id,
                    'agent': agent,
                    'message': message[:100],
                    'message_intent': message_intent,
                    'awaiting_final_answer': awaiting_final_answer,
                    'evaluation': evaluation.to_dict() if evaluation else None,
                    'trigger': trigger,
                    'switched': decision['switched']
                },
                'timestamp': datetime.now().isoformat()
            }, room='teacher_room')
            if trigger['triggered']:
                sio.emit('help_request', {
                    'student_id': student_id,
                    'student_name': profile['student_name'],
                    'question_id': question_id,
                    'content': build_teacher_notice(profile, trigger, 'answer' if evaluation and not getattr(evaluation, 'skip_evaluation', False) else 'chat', message),
                    'trigger_event_id': trigger_event_id,
                    'timestamp': datetime.now().isoformat()
                }, room='teacher_room')
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'response': response_text,
            'reply': response_text,
            'agent': agent,
            'response_source': response_source,
            'evaluation': evaluation.to_dict() if evaluation else None,
            'evaluation_source': evaluation_source,
            'message_intent': message_intent,
            'awaiting_final_answer': awaiting_final_answer,
            'next_question': next_question,
            'triggered': trigger['triggered'],
            'trigger_level': trigger['trigger_level'],
            'trigger_strength': trigger['trigger_strength'],
            'switched': decision['switched'],
            'explanation': decision['explanation'],
            'teacher_alert': decision['teacher_alert'],
            'mode_note': decision['mode_note']
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/history', methods=['GET'])
def get_history():
    """
    获取聊天历史
    
    参数：
    - question_id: 题目ID（可选）
    
    响应：
    {
        "success": true,
        "messages": [
            {"agent": "user", "content": "...", "time": "..."},
            {"agent": "Guide", "content": "...", "time": "..."}
        ]
    }
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403
    
    try:
        student_id = session['user_id']
        question_id = request.args.get('question_id')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if question_id:
            cursor.execute('''
                SELECT agent_name, message_type, content, created_at, override_id
                FROM chat_messages 
                WHERE student_id = ? AND question_id = ?
                ORDER BY created_at ASC
            ''', (student_id, question_id))
        else:
            cursor.execute('''
                SELECT agent_name, message_type, content, created_at, override_id
                FROM chat_messages 
                WHERE student_id = ?
                ORDER BY created_at DESC
                LIMIT 100
            ''', (student_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'agent': row[0],
                'type': row[1],
                'content': row[2],
                'time': serialize_timestamp(row[3]),
                'override_id': row[4],
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'messages': messages
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/overrides', methods=['GET'])
def get_overrides():
    """获取当前学生的教师 Override 列表和新消息。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403

    try:
        student_id = session['user_id']
        last_override_id = request.args.get('last_override_id', default=0, type=int)
        question_id = request.args.get('question_id', type=int)
        limit = request.args.get('limit', default=20, type=int)
        limit = min(max(limit, 1), 50)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, teacher_id, override_type, intervention_type, content,
                   question_id, created_at, status, trigger_event_id, feedback, feedback_at
            FROM teacher_overrides
            WHERE student_id = ?
              AND teacher_id != 0
              AND (? IS NULL OR question_id = ?)
            ORDER BY id DESC
            LIMIT ?
        ''', (student_id, question_id, question_id, limit))
        overrides = [dict(row) for row in cursor.fetchall()]

        cursor.execute('''
            SELECT id, teacher_id, override_type, intervention_type, content,
                   question_id, created_at, status, trigger_event_id, feedback, feedback_at
            FROM teacher_overrides
            WHERE student_id = ?
              AND teacher_id != 0
              AND id > ?
              AND (? IS NULL OR question_id = ?)
            ORDER BY id ASC
        ''', (student_id, last_override_id, question_id, question_id))
        new_overrides = [dict(row) for row in cursor.fetchall()]
        latest_override_id = max([row['id'] for row in overrides], default=last_override_id)
        conn.close()

        return jsonify({
            'success': True,
            'overrides': overrides,
            'new_overrides': new_overrides,
            'latest_override_id': latest_override_id,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/overrides/<int:override_id>/feedback', methods=['POST'])
def submit_override_feedback(override_id):
    """记录学生对教师 Override 的反馈。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403

    try:
        data = request.get_json(silent=True) or {}
        feedback_type = data.get('feedback_type')
        if feedback_type not in ['helpful', 'unclear']:
            return jsonify({'success': False, 'error': '反馈类型无效'}), 400

        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM teacher_overrides WHERE id = ? AND student_id = ? AND teacher_id != 0',
            (override_id, student_id)
        )
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Override不存在'}), 404

        cursor.execute(
            'UPDATE teacher_overrides SET feedback = ?, feedback_at = ? WHERE id = ?',
            (feedback_type, datetime.now().isoformat(), override_id)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'override_id': override_id, 'feedback': feedback_type})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/history/clear', methods=['POST'])
def clear_history():
    """清空当前登录学生某一道题的聊天历史。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403

    try:
        data = request.get_json(silent=True) or {}
        question_id = data.get('question_id')
        if question_id is None:
            return jsonify({'success': False, 'error': '缺少 question_id'}), 400

        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM chat_messages WHERE student_id = ? AND question_id = ?',
            (student_id, question_id)
        )
        deleted_messages = cursor.rowcount
        cursor.execute(
            'DELETE FROM teacher_overrides WHERE student_id = ? AND question_id = ?',
            (student_id, question_id)
        )
        deleted_overrides = cursor.rowcount
        cursor.execute(
            'DELETE FROM evaluation_records WHERE student_id = ? AND question_id = ?',
            (student_id, question_id)
        )
        deleted_evaluations = cursor.rowcount
        cursor.execute(
            'DELETE FROM student_progress WHERE student_id = ? AND question_id = ?',
            (student_id, question_id)
        )
        deleted_progress = cursor.rowcount
        cursor.execute(
            '''
            UPDATE student_states
            SET current_agent = 'Guide',
                error_streak = 0,
                last_error_type = 'none',
                consecutive_correct = 0,
                last_trigger_level = NULL,
                updated_at = ?
            WHERE student_id = ?
            ''',
            (datetime.now().isoformat(), student_id),
        )
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'deleted': deleted_messages + deleted_overrides + deleted_evaluations + deleted_progress,
            'deleted_messages': deleted_messages,
            'deleted_overrides': deleted_overrides,
            'deleted_evaluations': deleted_evaluations,
            'deleted_progress': deleted_progress,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/info', methods=['GET'])
def get_info():
    """获取学生个人信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    if session.get('role') != 'student':
        return jsonify({'success': False, 'error': '仅限学生使用'}), 403
    try:
        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT student_id, student_name, class_id, experiment_group, current_question, total_questions '
            'FROM student_assignments WHERE student_id = ?',
            (student_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({'success': False, 'error': '学生信息不存在'}), 404
        user_info = {
            'user_id': row[0],
            'name': row[1],
            'class_id': row[2],
            'condition': row[3],
            'experiment_group': row[3],
            'current_question': row[4] or 1,
            'total_questions': row[5] or 9
        }
        return jsonify({
            'success': True,
            'student_id': row[0],
            'student_name': row[1],
            'class_id': row[2],
            'experiment_group': row[3],
            'current_question': row[4] or 1,
            'total_questions': row[5] or 9,
            'user_info': user_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/condition', methods=['GET'])
def get_condition():
    """获取学生实验条件"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    try:
        student_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT experiment_group, current_question, total_questions FROM student_assignments WHERE student_id = ?',
            (student_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({'success': False, 'error': '学生信息不存在'}), 404
        return jsonify({
            'success': True,
            'experiment_group': row[0],
            'current_question': row[1] or 1,
            'total_questions': row[2] or 9
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/list', methods=['GET'])
def get_student_list():
    """获取学生列表（教师/管理员用）"""
    role = session.get('role')
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT
                sa.student_id,
                sa.student_name,
                sa.class_id,
                sa.experiment_group,
                sa.current_question,
                sa.total_questions,
                u.created_at,
                COALESCE(ss.current_agent, 'Guide') AS current_agent,
                COALESCE((
                    SELECT COUNT(*)
                    FROM teacher_overrides to2
                    WHERE to2.student_id = sa.student_id
                      AND to2.status = 'help_request'
                ), 0) AS pending_count,
                (
                    SELECT cm.content
                    FROM chat_messages cm
                    WHERE cm.student_id = sa.student_id
                    ORDER BY cm.created_at DESC, cm.id DESC
                    LIMIT 1
                ) AS last_message,
                (
                    SELECT cm.created_at
                    FROM chat_messages cm
                    WHERE cm.student_id = sa.student_id
                    ORDER BY cm.created_at DESC, cm.id DESC
                    LIMIT 1
                ) AS last_activity
            FROM student_assignments sa
            JOIN users u ON sa.student_id = u.user_id
            LEFT JOIN student_states ss ON sa.student_id = ss.student_id
            ORDER BY sa.student_id
            '''
        )
        students = []
        for row in cursor.fetchall():
            students.append({
                'student_id': row[0],
                'user_id': row[0],
                'student_name': row[1],
                'name': row[1],
                'class_id': row[2],
                'experiment_group': row[3],
                'condition': row[3],
                'current_question': row[4] or 1,
                'total_questions': row[5] or 9,
                'created_at': row[6],
                'current_agent': row[7] or 'Guide',
                'pending_count': row[8] or 0,
                'last_message': row[9],
                'last_activity': row[10],
            })
        conn.close()
        return jsonify({'success': True, 'students': students, 'total': len(students)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@student_bp.route('/stats', methods=['GET'])
def get_student_stats():
    """获取学生统计（教师/管理员用）"""
    role = session.get('role')
    if role not in ['teacher', 'admin_exp', 'admin_sys']:
        return jsonify({'success': False, 'error': '权限不足'}), 403
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM student_assignments')
        total_students = cursor.fetchone()[0]
        cursor.execute(
            'SELECT sp.student_id, sa.student_name, COUNT(sp.id) as total_attempts,'
            '  SUM(CASE WHEN sp.is_correct = 1 THEN 1 ELSE 0 END) as correct_count '
            'FROM student_progress sp '
            'JOIN student_assignments sa ON sp.student_id = sa.student_id '
            'GROUP BY sp.student_id'
        )
        stats = []
        for row in cursor.fetchall():
            total = row[2] or 0
            correct = row[3] or 0
            stats.append({
                'student_id': row[0],
                'student_name': row[1],
                'total_attempts': total,
                'correct_count': correct,
                'accuracy': round(correct / total * 100, 1) if total > 0 else 0
            })
        conn.close()
        return jsonify({
            'success': True,
            'total_students': total_students,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

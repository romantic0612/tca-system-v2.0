# -*- coding: utf-8 -*-
"""
TCA-System V2.0 WebSocket事件处理
================================

实时通信事件：
- connect/disconnect: 连接管理
- student_update: 学生状态更新推送
- teacher_override: 教师干预推送
- help_request: 求助通知推送
"""

from flask_socketio import emit, join_room, leave_room, rooms
from flask import request, session
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database.schema import get_connection

# 全局 socketio 实例（由 register_socket_events 设置）
_socketio_instance = None

def get_socketio():
    """获取全局 SocketIO 实例，供外部蓝图 WebSocket 推送使用"""
    global _socketio_instance
    return _socketio_instance

def register_socket_events(socketio):
    global _socketio_instance
    _socketio_instance = socketio
    
    @socketio.on('connect')
    def handle_connect():
        """
        客户端连接
        
        前端连接时需携带session cookie，自动识别用户身份
        """
        if 'user_id' not in session:
            return False
        
        user_id = session['user_id']
        role = session['role']
        
        if role == 'student':
            join_room(f'student_{user_id}')
            join_room('students_all')
            emit('connected', {
                'status': 'success',
                'user_id': user_id,
                'role': role,
                'room': f'student_{user_id}'
            })
        elif role == 'teacher':
            join_room('teacher_room')
            emit('connected', {
                'status': 'success',
                'user_id': user_id,
                'role': role,
                'room': 'teacher_room'
            })
        elif role in ['admin_exp', 'admin_sys']:
            join_room('admin_room')
            join_room('teacher_room')
            emit('connected', {
                'status': 'success',
                'user_id': user_id,
                'role': role,
                'room': 'admin_room'
            })
        
        print(f"[WS] 用户 {user_id} ({role}) 已连接")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        if 'user_id' in session:
            user_id = session['user_id']
            print(f"[WS] 用户 {user_id} 已断开")
    
    @socketio.on('join_room')
    def handle_join_room(data):
        """
        加入指定房间
        
        参数:
            room: 房间名（如 'question_3' 表示题目3的讨论组）
        """
        room_name = data.get('room')
        if room_name:
            join_room(room_name)
            emit('room_joined', {'room': room_name})
    
    @socketio.on('student_update')
    def handle_student_update(data):
        """
        学生状态更新事件
        
        学生提交答案、切换题目等操作时触发
        推送给教师端监控
        
        参数:
            student_id: 学号
            action: 动作类型（submit_answer, change_question, chat等）
            data: 详细数据
        
        推送给教师房间
        """
        role = session.get('role')
        if role not in ['student', 'teacher', 'admin_exp', 'admin_sys']:
            emit('error', {'message': '权限不足'})
            return
        
        student_id = data.get('student_id', session.get('user_id'))
        action = data.get('action')
        update_data = data.get('data', {})
        
        if not student_id or not action:
            emit('error', {'message': '参数不完整'})
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT student_name, experiment_group, current_question FROM student_assignments WHERE student_id = ?',
            (student_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        student_name = row[0] if row else '未知'
        experiment_group = row[1] if row else '未知'
        current_question = row[2] if row else 1
        
        payload = {
            'student_id': student_id,
            'student_name': student_name,
            'experiment_group': experiment_group,
            'current_question': current_question,
            'action': action,
            'data': update_data,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('student_update', payload, room='teacher_room')
        print(f"[WS] 学生 {student_id} 状态更新: {action}")
    
    @socketio.on('teacher_override')
    def handle_teacher_override(data):
        """
        教师干预事件
        
        教师发送干预指令，推送给指定学生
        
        参数:
            student_id: 目标学号
            override_type: 干预类型（hint, guidance, stop等）
            content: 干预内容
            target_agent: 目标智能体
        
        推送给学生房间
        """
        role = session.get('role')
        if role not in ['teacher', 'admin_exp', 'admin_sys']:
            emit('error', {'message': '权限不足，仅教师可使用干预功能'})
            return
        
        student_id = data.get('student_id')
        override_type = data.get('override_type', 'hint')
        content = data.get('content')
        target_agent = data.get('target_agent', 'Guide')
        
        if not student_id or not content:
            emit('error', {'message': '参数不完整'})
            return
        
        teacher_id = session.get('user_id')
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO teacher_overrides 
            (student_id, teacher_id, override_type, content, created_at, status)
            VALUES (?, ?, ?, ?, ?, 'active')
        ''', (student_id, teacher_id, override_type, content, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        payload = {
            'teacher_id': teacher_id,
            'override_type': override_type,
            'content': content,
            'target_agent': target_agent,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('teacher_override', payload, room=f'student_{student_id}')
        emit('override_sent', {'student_id': student_id, 'success': True})
        print(f"[WS] 教师 {teacher_id} 向学生 {student_id} 发送干预: {override_type}")
    
    @socketio.on('help_request')
    def handle_help_request(data):
        """
        求助事件
        
        学生发起求助，推送给教师端
        
        参数:
            question_id: 题目ID
            content: 求助内容
        
        推送给教师房间
        """
        student_id = session.get('user_id')
        question_id = data.get('question_id')
        content = data.get('content', '学生请求帮助')
        
        if not student_id:
            emit('error', {'message': '未登录'})
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT student_name FROM student_assignments WHERE student_id = ?', (student_id,))
        row = cursor.fetchone()
        student_name = row[0] if row else '未知'
        
        cursor.execute('''
            INSERT INTO teacher_overrides 
            (student_id, teacher_id, override_type, content, question_id, created_at, status)
            VALUES (?, 0, 'help_request', ?, ?, ?, 'help_request')
        ''', (student_id, content, question_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        payload = {
            'student_id': student_id,
            'student_name': student_name,
            'question_id': question_id,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('help_request', payload, room='teacher_room')
        emit('help_sent', {'success': True})
        print(f"[WS] 学生 {student_id} 发起求助: 题目{question_id}")
    
    @socketio.on('agent_response')
    def handle_agent_response(data):
        """
        智能体响应事件
        
        智能体回复推送给学生
        
        参数:
            student_id: 学号
            agent_name: 智能体名称
            response: 响应内容
        """
        student_id = data.get('student_id')
        agent_name = data.get('agent_name', 'Guide')
        response = data.get('response')
        question_id = data.get('question_id')
        
        if not student_id or not response:
            return
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_messages 
            (student_id, agent_name, message_type, content, question_id, created_at)
            VALUES (?, ?, 'agent', ?, ?, ?)
        ''', (student_id, agent_name, response, question_id, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        payload = {
            'agent_name': agent_name,
            'response': response,
            'question_id': question_id,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('agent_response', payload, room=f'student_{student_id}')
    
    print("[WS] WebSocket事件已注册")
    return socketio

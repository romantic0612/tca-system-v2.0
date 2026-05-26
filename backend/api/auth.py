# -*- coding: utf-8 -*-
"""
TCA-System V2.0 认证API
======================

登录、登出、会话验证
"""

from flask import Blueprint, request, jsonify, session
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database.schema import get_connection
from backend.core.auth.auth_manager import AuthManager

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    
    请求体：
    {
        "user_id": 20240001,
        "password": "123456"
    }
    
    响应：
    {
        "success": true,
        "role": "student",
        "user_id": 20240001,
        "redirect": "/student.html"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id') or data.get('username')
        password = data.get('password')
        
        if not user_id or not password:
            return jsonify({'success': False, 'error': '请输入账号和密码'}), 400
        
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': '账号必须为数字'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        auth = AuthManager()
        success, role, message = auth.authenticate(user_id, password, cursor)
        
        if not success:
            conn.close()
            return jsonify({'success': False, 'error': message}), 401
        
        session['user_id'] = user_id
        session['role'] = role
        session.permanent = True
        
        cursor.execute(
            'SELECT student_name, experiment_group FROM student_assignments WHERE student_id = ?',
            (user_id,)
        )
        student_info = cursor.fetchone()
        conn.close()
        
        redirect_map = {
            'student': '/student.html',
            'teacher': '/teacher.html',
            'admin_exp': '/admin.html',
            'admin_sys': '/admin.html'
        }
        
        response_data = {
            'success': True,
            'role': role,
            'user_id': user_id,
            'redirect': redirect_map.get(role, '/')
        }
        
        if student_info:
            response_data['student_name'] = student_info[0]
            response_data['experiment_group'] = student_info[1]
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.clear()
    return jsonify({'success': True, 'redirect': '/login.html'})


@auth_bp.route('/check', methods=['GET'])
def check_session():
    """
    检查会话状态
    
    响应：
    {
        "success": true,
        "logged_in": true,
        "user_id": 20240001,
        "role": "student"
    }
    """
    if 'user_id' not in session:
        return jsonify({
            'success': True,
            'logged_in': False
        })
    
    user_info = {
        'user_id': session['user_id'],
        'role': session['role']
    }

    return jsonify({
        'success': True,
        'logged_in': True,
        'user_id': session['user_id'],
        'role': session['role'],
        'user_info': user_info
    })


@auth_bp.route('/validate/<int:user_id>', methods=['GET'])
def validate(user_id):
    """验证账号格式"""
    from backend.core.auth.auth_manager import AuthManager
    auth = AuthManager()
    valid, role = auth.validate_user_id(user_id)
    return jsonify({
        'success': valid,
        'role': role if valid else None,
        'format_valid': valid
    })

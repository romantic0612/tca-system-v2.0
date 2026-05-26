# -*- coding: utf-8 -*-
"""
TCA-System V2.0 认证管理器
=========================

账号格式验证：
- 学号：8位数字
- 教师工号：6位数字，1开头
- 管理员工号：6位数字，9开头
"""

import hashlib
import re

class AuthManager:
    
    @staticmethod
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return AuthManager.hash_password(password) == password_hash
    
    @staticmethod
    def validate_student_id(student_id: int) -> bool:
        student_str = str(student_id)
        return len(student_str) == 8 and student_str.isdigit()
    
    @staticmethod
    def validate_teacher_id(teacher_id: int) -> bool:
        teacher_str = str(teacher_id)
        return len(teacher_str) == 6 and teacher_str[0] == '1' and teacher_str.isdigit()
    
    @staticmethod
    def validate_admin_id(admin_id: int) -> bool:
        admin_str = str(admin_id)
        return len(admin_str) == 6 and admin_str[0] == '9' and admin_str.isdigit()
    
    @staticmethod
    def get_role_from_id(user_id: int) -> str:
        user_str = str(user_id)
        if len(user_str) == 8 and user_str.isdigit():
            return 'student'
        elif len(user_str) == 6 and user_str.isdigit():
            if user_str[0] == '1':
                return 'teacher'
            elif user_str[0] == '9':
                return 'admin_sys'
        return None
    
    @staticmethod
    def validate_user_id(user_id: int) -> tuple[bool, str]:
        role = AuthManager.get_role_from_id(user_id)
        if role is None:
            return False, "无效的账号格式"
        return True, role
    
    def authenticate(self, user_id: int, password: str, cursor) -> tuple[bool, str, str]:
        valid, role = self.validate_user_id(user_id)
        if not valid:
            return False, None, "账号格式无效"
        
        cursor.execute(
            'SELECT password_hash, role FROM users WHERE user_id = ?',
            (user_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return False, None, "账号不存在"
        
        if not self.verify_password(password, row[0]):
            return False, None, "密码错误"
        
        return True, row[1], "认证成功"

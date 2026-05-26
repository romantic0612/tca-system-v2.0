# -*- coding: utf-8 -*-
"""
TCA-System V2.0 Flask测试脚本
============================

测试Flask应用基础功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_app_creation():
    print("\n【测试1】创建Flask应用...")
    from backend.app import create_app
    app, _ = create_app()
    assert app is not None, "应用创建失败"
    print("  ✅ 应用创建成功")
    return app

def test_routes(app):
    print("\n【测试2】检查路由...")
    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            routes.append(f"{rule.rule} -> {list(rule.methods - {'HEAD', 'OPTIONS'})}")
    
    expected_routes = [
        '/api/auth/login',
        '/api/auth/logout',
        '/api/auth/check',
        '/api/student/progress',
        '/api/student/submit-answer',
        '/api/student/chat',
        '/api/student/history',
        '/api/teacher/intervene',
        '/api/teacher/help-request',
        '/api/teacher/help-requests'
    ]
    
    found = 0
    for expected in expected_routes:
        if any(expected in r for r in routes):
            found += 1
            print(f"  ✅ {expected}")
    
    assert found == len(expected_routes), f"路由不完整，期望{len(expected_routes)}，找到{found}"
    print(f"  ✅ 共{found}个API路由注册成功")
    return routes

def test_database():
    print("\n【测试3】检查数据库...")
    from backend.core.database.schema import get_connection, init_database, create_test_users
    
    init_database()
    create_test_users()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    print(f"  ✅ 用户数量: {user_count}")
    
    cursor.execute('SELECT user_id, role FROM users')
    users = cursor.fetchall()
    for user in users:
        print(f"    - {user[0]} ({user[1]})")
    
    conn.close()
    assert user_count >= 6, "测试用户创建失败"
    return True

def test_auth():
    print("\n【测试4】测试认证...")
    from backend.core.auth.auth_manager import AuthManager
    from backend.core.database.schema import get_connection
    
    auth = AuthManager()
    conn = get_connection()
    cursor = conn.cursor()
    
    success, role, msg = auth.authenticate(20240001, '123456', cursor)
    assert success, f"学生登录失败: {msg}"
    print(f"  ✅ 学生登录成功: {role}")
    
    success, role, msg = auth.authenticate(100001, 'teacher123', cursor)
    assert success, f"教师登录失败: {msg}"
    print(f"  ✅ 教师登录成功: {role}")
    
    success, role, msg = auth.authenticate(900001, 'admin123', cursor)
    assert success, f"管理员登录失败: {msg}"
    print(f"  ✅ 管理员登录成功: {role}")
    
    conn.close()
    return True

def main():
    print("\n" + "="*60)
    print("  TCA-System V2.0 Flask测试")
    print("="*60)
    
    try:
        app = test_app_creation()
        routes = test_routes(app)
        test_database()
        test_auth()
        
        print("\n" + "="*60)
        print("  ✅ 所有测试通过！")
        print("="*60)
        print(f"\n  启动命令: python start.py")
        print(f"  访问地址: http://127.0.0.1:5000")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n  ❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

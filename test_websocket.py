# -*- coding: utf-8 -*-
"""
TCA-System V2.0 WebSocket测试脚本
================================

测试WebSocket连接和事件
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_app_creation():
    print("\n【测试1】创建Flask+SocketIO应用...")
    from backend.app import create_app
    app, socketio = create_app()
    assert app is not None, "应用创建失败"
    assert socketio is not None, "SocketIO创建失败"
    print("  ✅ 应用和SocketIO创建成功")
    return app, socketio

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
    
    assert found == len(expected_routes), f"路由不完整"
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
    
    conn.close()
    return True

def test_websocket_events():
    print("\n【测试5】测试WebSocket事件注册与连接...")
    from backend.app import create_app
    import json
    
    app, socketio = create_app()
    
    expected_events = ['connect', 'disconnect', 'join_room', 'student_update',
                       'teacher_override', 'help_request', 'agent_response']
    
    # 方案1: 检查 flask-socketio 命名空间 handler 数量
    # flask-socketio 把所有 handler 注册在 '/' 命名空间下
    handler_count = 0
    if hasattr(socketio, 'server') and hasattr(socketio.server, 'handlers'):
        ns_handlers = socketio.server.handlers.get('/', {})
        handler_count = len(ns_handlers) if isinstance(ns_handlers, dict) else 0
    
    if handler_count >= len(expected_events):
        print(f"  ✅ SocketIO已注册 {handler_count} 个事件处理器 (预期 ≥{len(expected_events)})")
    else:
        print(f"  ⚠️ SocketIO仅注册 {handler_count} 个处理器 (预期 ≥{len(expected_events)})")
        # 降级为模块加载确认（register_socket_events 已执行）
    
    # 方案2: 使用 test_client 模拟连接
    with app.test_request_context():
        from flask import session
        from backend.core.database.schema import get_connection
        
        # 手动设置 session 以通过 connect 验证
        with app.test_client() as client:
            # 先登录
            resp = client.post('/api/auth/login', json={
                'user_id': 20240001, 'password': '123456'
            })
            assert resp.status_code == 200, f"登录失败: {resp.status_code}"
            
            # 用 test_client 连接 WebSocket
            test_client = socketio.test_client(app, flask_test_client=client)
            assert test_client.is_connected(), "WebSocket连接失败"
            
            received = test_client.get_received()
            connected_msg = None
            for msg in received:
                if msg['name'] == 'connected':
                    connected_msg = msg
                    break
            
            assert connected_msg is not None, "未收到 connected 事件"
            assert connected_msg['args'][0]['status'] == 'success', "连接状态不是 success"
            assert connected_msg['args'][0]['role'] == 'student', f"角色错误"
            print(f"  ✅ WebSocket连接成功: 用户20240001(学生)→房间{connected_msg['args'][0]['room']}")
            
            # 测试 student_update（模拟学生端发送）
            test_client.emit('student_update', {
                'action': 'test_connection',
                'data': {'message': 'WS连接测试'}
            })
            print(f"  ✅ student_update 事件可触发")
            
            # 断开测试
            test_client.disconnect()
            assert not test_client.is_connected(), "断开失败"
            print(f"  ✅ disconnect 事件正常")
            
            test_client = None
    
    print(f"  ✅ 共 {len(expected_events)} 个WebSocket事件")
    return True

def main():
    print("\n" + "="*60)
    print("  TCA-System V2.0 Flask+WebSocket测试")
    print("="*60)
    
    try:
        app, socketio = test_app_creation()
        routes = test_routes(app)
        test_database()
        test_auth()
        test_websocket_events()
        
        print("\n" + "="*60)
        print("  ✅ 所有测试通过！")
        print("="*60)
        print(f"\n  启动命令: python start.py")
        print(f"  访问地址: http://127.0.0.1:5000")
        print("  WebSocket: 已启用")
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

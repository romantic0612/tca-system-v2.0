# -*- coding: utf-8 -*-
"""
TCA-System V2.0 Flask应用工厂
============================

创建并配置Flask应用实例，集成WebSocket
"""

from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from backend.core.database.schema import init_database, create_default_accounts

socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'static'),
        static_url_path=''
    )
    
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SESSION_COOKIE_NAME'] = config.SESSION_COOKIE_NAME
    app.config['SESSION_COOKIE_HTTPONLY'] = config.SESSION_COOKIE_HTTPONLY
    app.config['PERMANENT_SESSION_LIFETIME'] = config.PERMANENT_SESSION_LIFETIME
    
    init_database()
    create_default_accounts()
    
    from backend.api.auth import auth_bp
    from backend.api.student import student_bp
    from backend.api.teacher import teacher_bp
    from backend.api.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(teacher_bp, url_prefix='/api/teacher')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'login.html')
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        return send_from_directory(app.static_folder, filename)
    
    @app.route('/api')
    def api_info():
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    'path': rule.rule,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'})
                })
        return {
            'name': 'TCA-System V2.0',
            'version': '2.0.0',
            'websocket': True,
            'routes_count': len(routes),
            'routes': routes
        }
    
    socketio.init_app(app)
    
    from backend.websocket.events import register_socket_events
    register_socket_events(socketio)
    
    return app, socketio


def create_app_simple():
    app, _ = create_app()
    return app


if __name__ == '__main__':
    app, socketio = create_app()
    print(f"\n{'='*60}")
    print("  TCA-System V2.0 启动成功")
    print(f"  地址: http://{config.HOST}:{config.PORT}")
    print("  WebSocket: 已启用")
    print(f"{'='*60}\n")
    socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG, allow_unsafe_werkzeug=True)

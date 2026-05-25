# -*- coding: utf-8 -*-
"""
TCA-System V2.0 Flask应用工厂
============================

创建并配置Flask应用实例，集成WebSocket
"""

from flask import Flask, abort, send_from_directory
from flask_socketio import SocketIO
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import config
from backend.core.database.schema import init_database, create_default_accounts

socketio = SocketIO(cors_allowed_origins="*")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VUE_DIST_DIR = os.path.join(ROOT_DIR, 'frontend', 'vue-app', 'dist')
STATIC_DIR = os.path.join(ROOT_DIR, 'frontend', 'static')


def get_frontend_dir():
    """Choose the product frontend.

    The static frontend is currently the functional product UI. The Vue app is
    kept as the V2.0 refactor workspace and can be enabled explicitly when it
    has feature parity.
    """
    frontend_mode = os.getenv('TCA_FRONTEND_MODE', 'static').strip().lower()
    if frontend_mode == 'vue':
        vue_index = os.path.join(VUE_DIST_DIR, 'index.html')
        if os.path.exists(vue_index):
            return VUE_DIST_DIR
        print('[WARN] TCA_FRONTEND_MODE=vue but Vue dist is missing; fallback to static frontend.')
    return STATIC_DIR


def is_vue_frontend(frontend_dir):
    vue_index = os.path.join(VUE_DIST_DIR, 'index.html')
    return os.path.abspath(frontend_dir) == os.path.abspath(VUE_DIST_DIR) and os.path.exists(vue_index)


def serve_frontend_file(frontend_dir, filename):
    if filename.startswith('api/'):
        abort(404)

    target_path = os.path.join(frontend_dir, filename)
    if os.path.exists(target_path) and os.path.isfile(target_path):
        return send_from_directory(frontend_dir, filename)

    if not is_vue_frontend(frontend_dir):
        route_map = {
            'login': 'login.html',
            'student': 'student.html',
            'teacher': 'teacher.html',
            'admin': 'admin.html',
        }
        if filename in route_map:
            return send_from_directory(frontend_dir, route_map[filename])
        abort(404)

    if os.path.exists(os.path.join(frontend_dir, 'index.html')):
        return send_from_directory(frontend_dir, 'index.html')

    abort(404)

def create_app():
    frontend_dir = get_frontend_dir()
    app = Flask(
        __name__,
        static_folder=None,
    )
    app.static_folder = frontend_dir
    
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
        if is_vue_frontend(app.static_folder):
            return send_from_directory(app.static_folder, 'index.html')
        return send_from_directory(app.static_folder, 'login.html')
    
    @app.route('/<path:filename>')
    def serve_static(filename):
        return serve_frontend_file(app.static_folder, filename)
    
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

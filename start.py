# -*- coding: utf-8 -*-
"""
TCA-System V2.0 启动脚本
=======================

快速启动Flask应用（含WebSocket）
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app
from config.settings import config

if __name__ == '__main__':
    app, socketio = create_app()
    
    print(f"\n{'='*60}")
    print("  TCA-System V2.0 - 教师可控多智能体AI辅导系统")
    print(f"{'='*60}")
    print(f"  地址: http://{config.HOST}:{config.PORT}")
    print(f"  模式: {'开发模式' if config.DEBUG else '生产模式'}")
    print("  WebSocket: 已启用")
    print(f"{'='*60}\n")
    print("  默认管理员:")
    print("    管理员: 900001 / admin123")
    print("  学生与教师账号请在管理端导入或创建")
    print(f"{'='*60}\n")
    
    socketio.run(
        app,
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        allow_unsafe_werkzeug=True
    )

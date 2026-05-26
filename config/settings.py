# -*- coding: utf-8 -*-
"""
TCA-System V2.0 配置模块
=======================

加载环境变量和应用配置
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'tca-dev-secret-key-2024')
    DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'data' / 'tca_system.db'))
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    HOST = os.getenv('HOST', '127.0.0.1')
    PORT = int(os.getenv('PORT', 5000))

    ECNU_LLM_BASE_URL = os.getenv('ECNU_LLM_BASE_URL', 'https://chat.ecnu.edu.cn/open/api/v1')
    ECNU_LLM_API_KEY = os.getenv('ECNU_LLM_API_KEY', '')
    ECNU_LLM_ENABLED = os.getenv('ECNU_LLM_ENABLED', 'true').lower() == 'true'
    ECNU_LLM_GUIDE_MODEL = os.getenv('ECNU_LLM_GUIDE_MODEL', 'ecnu-plus')
    ECNU_LLM_TUTOR_MODEL = os.getenv('ECNU_LLM_TUTOR_MODEL', 'ecnu-plus')
    ECNU_LLM_EVALUATOR_MODEL = os.getenv('ECNU_LLM_EVALUATOR_MODEL', 'ecnu-max')
    ECNU_LLM_TIMEOUT = int(os.getenv('ECNU_LLM_TIMEOUT', 20))
    
    EXPERIMENT_GROUPS = ['SA', 'EXP', 'AI-AUTO', 'TCA']
    
    SESSION_COOKIE_NAME = 'tca_session'
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 86400

config = Config()

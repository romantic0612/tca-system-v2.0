# -*- coding: utf-8 -*-
"""
Product flow tests for the current static TCA-System product UI/API.
"""

import csv
import io
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app
from backend.core.database.schema import create_test_users, init_database


def make_client():
    init_database()
    create_test_users()
    app, _ = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def login(client, user_id, password):
    resp = client.post('/api/auth/login', json={'user_id': user_id, 'password': password})
    data = resp.get_json()
    assert resp.status_code == 200, data
    assert data['success'], data
    return data


def test_tca_override_flow():
    print('\n【产品流】学生求助 -> 教师详情 -> TCA教师干预 -> 学生收到Override')
    client = make_client()

    login(client, 20240003, '123456')
    chat_resp = client.post('/api/student/chat', json={
        'message': '我不会，这道题卡住了',
        'question_id': 4,
        'agent': 'Guide',
    })
    chat_data = chat_resp.get_json()
    assert chat_resp.status_code == 200, chat_data
    assert chat_data['success'], chat_data
    client.post('/api/auth/logout')

    login(client, 100001, 'teacher123')
    help_resp = client.get('/api/teacher/help-requests')
    help_data = help_resp.get_json()
    assert help_data['success'], help_data
    assert any(int(item['student_id']) == 20240003 for item in help_data['requests']), help_data

    detail_resp = client.get('/api/teacher/event-detail?student_id=20240003&question_id=4')
    detail_data = detail_resp.get_json()
    assert detail_data['success'], detail_data
    assert detail_data['question_id'] == 4
    assert detail_data['student']['experiment_group'] == 'TCA'
    assert any(msg['type'] == 'user' and '不会' in msg['content'] for msg in detail_data['messages'])

    content = '测试提示：先写出三角形内角和是180°。'
    intervene_resp = client.post('/api/teacher/intervene', json={
        'student_id': 20240003,
        'question_id': 4,
        'target_agent': 'Tutor',
        'intervention_type': 'scaffold',
        'content': content,
    })
    intervene_data = intervene_resp.get_json()
    assert intervene_resp.status_code == 200, intervene_data
    assert intervene_data['success'], intervene_data
    override_id = intervene_data['override_id']
    client.post('/api/auth/logout')

    login(client, 20240003, '123456')
    overrides_resp = client.get('/api/student/overrides?question_id=4')
    overrides_data = overrides_resp.get_json()
    assert overrides_data['success'], overrides_data
    assert any(row['id'] == override_id and row['content'] == content for row in overrides_data['overrides'])
    print('  OK TCA端到端干预链路可用')


def test_non_tca_override_rejected():
    print('\n【权限】SA/EXP/AI-AUTO 仅观察，后端拒绝Override')
    client = make_client()
    login(client, 100001, 'teacher123')
    for student_id in [20240001, 20240002, 20240004]:
        resp = client.post('/api/teacher/intervene', json={
            'student_id': student_id,
            'question_id': 3,
            'target_agent': 'Tutor',
            'intervention_type': 'manual_override',
            'content': '这条不应该被发送',
        })
        data = resp.get_json()
        assert resp.status_code == 403, data
        assert not data['success'], data
    print('  OK 非TCA组后端权限边界生效')


def test_admin_import_validation_and_export():
    print('\n【管理端】CSV导入校验与实验数据导出')
    client = make_client()
    login(client, 900001, 'admin123')

    base_id = 20990000 + random.randint(100, 899)
    csv_text = (
        '学号,姓名,班级,前测成绩,组别,密码\n'
        f'{base_id},测试学生,一班,88,TCA,123456\n'
        f'{base_id},重复学生,一班,91,SA,123456\n'
        'bad-id,非法学号,一班,80,TCA,123456\n'
        f'{base_id + 1},,一班,80,TCA,123456\n'
        f'{base_id + 2},非法组别,一班,80,ABC,123456\n'
        f'{base_id + 3},非法成绩,一班,180,TCA,123456\n'
    )
    data = {
        'file': (io.BytesIO(csv_text.encode('utf-8-sig')), 'students.csv')
    }
    import_resp = client.post('/api/admin/students/import', data=data, content_type='multipart/form-data')
    import_data = import_resp.get_json()
    assert import_resp.status_code == 200, import_data
    assert import_data['success'], import_data
    assert import_data['success_count'] == 1, import_data
    assert import_data['failed_count'] == 5, import_data
    reasons = ' '.join(item['error'] for item in import_data['errors'])
    assert '重复学号' in reasons
    assert '学号必须是纯数字' in reasons
    assert '姓名不能为空' in reasons
    assert '组别不合法' in reasons
    assert '0-100' in reasons

    export_resp = client.get('/api/admin/export/experiment-data.csv')
    assert export_resp.status_code == 200
    text = export_resp.get_data(as_text=True)
    assert '[students]' in text
    assert '[chat_messages]' in text
    assert '[evaluation_records]' in text
    assert '[trigger_events]' in text
    assert '[teacher_overrides]' in text
    csv.reader(io.StringIO(text))
    print('  OK 导入错误可解释，实验数据CSV可导出')


def main():
    try:
        test_tca_override_flow()
        test_non_tca_override_rejected()
        test_admin_import_validation_and_export()
        print('\nOK 产品流测试全部通过')
        return 0
    except AssertionError as exc:
        print(f'\nFAIL 产品流测试失败: {exc}')
        return 1


if __name__ == '__main__':
    sys.exit(main())

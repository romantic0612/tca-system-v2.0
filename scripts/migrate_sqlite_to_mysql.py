# -*- coding: utf-8 -*-
"""
Copy existing SQLite data into the MySQL database configured in .env.

Usage inside the Docker container:
    python scripts/migrate_sqlite_to_mysql.py --sqlite /app/data/tca_system.db --replace
"""

import argparse
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TABLES = [
    'users',
    'student_assignments',
    'student_states',
    'student_progress',
    'trigger_events',
    'evaluation_records',
    'agent_switches',
    'teacher_overrides',
    'chat_messages',
]


def load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def sqlite_columns(cursor, table):
    cursor.execute(f'PRAGMA table_info({table})')
    return [row[1] for row in cursor.fetchall()]


def mysql_columns(cursor, table):
    cursor.execute(f'SHOW COLUMNS FROM {table}')
    return [row['Field'] for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sqlite', default=os.getenv('SQLITE_SOURCE', 'data/tca_system.db'))
    parser.add_argument('--replace', action='store_true', help='Clear MySQL tables before import.')
    args = parser.parse_args()

    load_dotenv(os.path.join(ROOT, '.env'))
    os.environ['DB_TYPE'] = 'mysql'

    from backend.core.database.schema import get_connection, init_database

    if not os.path.exists(args.sqlite):
        raise SystemExit(f'SQLite file not found: {args.sqlite}')

    init_database()

    src = sqlite3.connect(args.sqlite)
    src.row_factory = sqlite3.Row
    src_cursor = src.cursor()

    dst = get_connection()
    dst_cursor = dst.cursor()

    if args.replace:
        for table in reversed(TABLES):
            dst_cursor.execute(f'DELETE FROM {table}')
        dst.commit()

    for table in TABLES:
        src_cols = sqlite_columns(src_cursor, table)
        dst_cols = mysql_columns(dst_cursor, table)
        columns = [col for col in src_cols if col in dst_cols]
        if not columns:
            continue

        src_cursor.execute(f'SELECT {", ".join(columns)} FROM {table}')
        rows = src_cursor.fetchall()
        if not rows:
            print(f'{table}: 0')
            continue

        placeholders = ', '.join(['?'] * len(columns))
        column_sql = ', '.join(columns)
        inserted = 0
        for row in rows:
            dst_cursor.execute(
                f'INSERT IGNORE INTO {table} ({column_sql}) VALUES ({placeholders})',
                tuple(row[col] for col in columns),
            )
            inserted += 1
        dst.commit()
        print(f'{table}: {inserted}')

    src.close()
    dst.close()
    print('Migration complete.')


if __name__ == '__main__':
    main()

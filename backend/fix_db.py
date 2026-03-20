import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quiz_app.settings')
django.setup()

from django.db import connection

print("Adding missing columns to quizzes...")
with connection.cursor() as cursor:
    try:
        cursor.execute("ALTER TABLE quizzes ADD COLUMN category varchar(50) DEFAULT 'other' NOT NULL;")
        print("Added category")
    except Exception as e: print(e); connection.rollback()
    
    try:
        cursor.execute("ALTER TABLE quizzes ADD COLUMN time_limit_seconds integer DEFAULT 900 NOT NULL;")
        print("Added time_limit_seconds")
    except Exception as e: print(e); connection.rollback()

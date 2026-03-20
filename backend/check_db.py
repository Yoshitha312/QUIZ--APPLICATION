import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quiz_app.settings')
django.setup()

from django.db import connection
from django.apps import apps

print("Introspecting database tables...")
with connection.cursor() as cursor:
    for model in apps.get_models():
        table_name = model._meta.db_table
        if table_name in connection.introspection.table_names():
            columns = [col.name for col in connection.introspection.get_table_description(cursor, table_name)]
            for field in model._meta.concrete_fields:
                if field.column not in columns:
                    print(f"MISSING: {table_name}.{field.column} ({field.get_internal_type()})")

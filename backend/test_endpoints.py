import os
import django
from django.test import Client
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quiz_app.settings')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
client = Client(SERVER_NAME='127.0.0.1')

user = User.objects.first()
if not user:
    user = User.objects.create(email='unique_test@example.com', username='unique_testuser')

token = str(RefreshToken.for_user(user).access_token)

headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

endpoints = [
    '/api/v1/quizzes/categories/',
    '/api/v1/quizzes/',
    '/api/v1/analytics/leaderboard/',
]

for ep in endpoints:
    print(f"Testing {ep}...")
    try:
        response = client.get(ep, SERVER_NAME='127.0.0.1', **headers)
        print(f"Status: {response.status_code}")
        if response.status_code >= 400:
            print("Content:", response.content)
    except Exception as e:
        import traceback
        traceback.print_exc()

print("Testing /api/v1/quizzes/generate/ as authenticated user...")
try:
    response = client.post('/api/v1/quizzes/generate/', data={'topic': 'python', 'num_questions': 5, 'difficulty': 'medium'}, content_type='application/json', SERVER_NAME='127.0.0.1', **headers)
    print(f"Status: {response.status_code}")
    if response.status_code >= 400:
        print("Content:", response.content)
except Exception as e:
    import traceback
    traceback.print_exc()

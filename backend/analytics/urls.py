from django.urls import path
from . import views
urlpatterns = [
    path('dashboard/', views.UserDashboardView.as_view(), name='user-dashboard'),
    path('quiz/<int:quiz_id>/', views.QuizAnalyticsView.as_view(), name='quiz-analytics'),
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('leaderboard/', views.LeaderboardView.as_view(), name='leaderboard'),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.QuizViewSet, basename='quiz')

urlpatterns = [
    path('generate/', views.GenerateQuizView.as_view(), name='generate-quiz'),
    path('generation-requests/', views.GenerationRequestListView.as_view(), name='generation-requests'),
    path('my-quizzes/', views.MyQuizzesView.as_view(), name='my-quizzes'),
    path('categories/', views.QuizByCategoryView.as_view(), name='quiz-categories'),
    path('my-attempts/', views.UserAttemptHistoryView.as_view(), name='my-attempts'),
    path('attempts/<int:attempt_id>/answer/', views.SubmitAnswerView.as_view(), name='submit-answer'),
    path('attempts/<int:attempt_id>/complete/', views.CompleteAttemptView.as_view(), name='complete-attempt'),
    path('attempts/<int:attempt_id>/timeout/', views.TimeoutAttemptView.as_view(), name='timeout-attempt'),
    path('attempts/<int:pk>/', views.AttemptDetailView.as_view(), name='attempt-detail'),
    path('<int:quiz_id>/questions/', views.QuizQuestionsView.as_view(), name='quiz-questions'),
    path('<int:quiz_id>/attempt/', views.QuizAttemptView.as_view(), name='start-attempt'),
    path('', include(router.urls)),
]

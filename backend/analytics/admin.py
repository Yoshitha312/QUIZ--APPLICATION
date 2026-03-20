from django.contrib import admin
from .models import QuizAnalytics


@admin.register(QuizAnalytics)
class QuizAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'total_attempts', 'completed_attempts', 'pass_rate', 'average_score', 'updated_at')
    readonly_fields = ('pass_rate', 'completion_rate')

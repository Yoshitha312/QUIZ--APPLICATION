from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class QuizAnalytics(models.Model):
    """Aggregated analytics per quiz."""
    quiz = models.OneToOneField('quizzes.Quiz', on_delete=models.CASCADE, related_name='analytics')
    total_attempts = models.IntegerField(default=0)
    completed_attempts = models.IntegerField(default=0)
    pass_count = models.IntegerField(default=0)
    fail_count = models.IntegerField(default=0)
    average_score = models.FloatField(default=0.0)
    highest_score = models.FloatField(default=0.0)
    lowest_score = models.FloatField(default=0.0)
    average_time_seconds = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'quiz_analytics'
        verbose_name_plural = 'Quiz Analytics'

    def __str__(self):
        return f"Analytics: {self.quiz.title}"

    @property
    def pass_rate(self):
        if self.completed_attempts == 0:
            return 0
        return round(self.pass_count / self.completed_attempts * 100, 2)

    @property
    def completion_rate(self):
        if self.total_attempts == 0:
            return 0
        return round(self.completed_attempts / self.total_attempts * 100, 2)

    def refresh_from_attempts(self):
        """Recalculate analytics from all completed attempts."""
        from quizzes.models import QuizAttempt
        from django.db.models import Avg, Max, Min, Count

        attempts = QuizAttempt.objects.filter(quiz=self.quiz)
        completed = attempts.filter(status='completed')

        stats = completed.aggregate(
            avg_score=Avg('percentage'),
            max_score=Max('percentage'),
            min_score=Min('percentage'),
            avg_time=Avg('time_taken_seconds'),
        )

        self.total_attempts = attempts.count()
        self.completed_attempts = completed.count()
        self.pass_count = completed.filter(passed=True).count()
        self.fail_count = completed.filter(passed=False).count()
        self.average_score = stats['avg_score'] or 0
        self.highest_score = stats['max_score'] or 0
        self.lowest_score = stats['min_score'] or 0
        self.average_time_seconds = stats['avg_time'] or 0
        self.save()

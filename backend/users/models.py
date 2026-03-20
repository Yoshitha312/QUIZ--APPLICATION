from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)
    is_email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        return self.role == 'admin' or self.is_staff

    @property
    def is_teacher(self):
        return self.role in ('teacher', 'admin') or self.is_staff


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    total_quizzes_taken = models.IntegerField(default=0)
    total_score = models.FloatField(default=0.0)
    average_score = models.FloatField(default=0.0)
    best_score = models.FloatField(default=0.0)
    streak_days = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_profiles'

    def update_stats(self, new_score):
        self.total_quizzes_taken += 1
        self.total_score += new_score
        self.average_score = self.total_score / self.total_quizzes_taken
        if new_score > self.best_score:
            self.best_score = new_score
        self.save()

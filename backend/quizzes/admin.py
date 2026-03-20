from django.contrib import admin
from .models import Quiz, Question, QuestionOption, QuizAttempt, UserAnswer, QuizGenerationRequest


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'difficulty', 'status', 'is_ai_generated', 'question_count', 'created_by', 'created_at')
    list_filter = ('difficulty', 'status', 'is_ai_generated')
    search_fields = ('title', 'topic')
    inlines = [QuestionInline]

    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'question_text', 'question_type', 'points', 'order')
    list_filter = ('question_type',)
    inlines = [QuestionOptionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'status', 'score', 'percentage', 'passed', 'started_at')
    list_filter = ('status', 'passed')
    search_fields = ('user__email', 'quiz__title')
    readonly_fields = ('score', 'percentage', 'passed', 'time_taken_seconds')


@admin.register(QuizGenerationRequest)
class QuizGenerationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'num_questions', 'difficulty', 'status', 'created_at')
    list_filter = ('status', 'difficulty')
    readonly_fields = ('generated_quiz', 'error_message', 'completed_at')

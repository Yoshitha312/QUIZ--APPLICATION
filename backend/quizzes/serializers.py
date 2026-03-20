from rest_framework import serializers
from .models import Quiz, Question, QuestionOption, QuizAttempt, UserAnswer, QuizGenerationRequest

class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('id','option_text','order')

class QuestionOptionFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('id','option_text','is_correct','order')

class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    class Meta:
        model = Question
        fields = ('id','question_text','question_type','points','order','options')

class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)
    time_limit_minutes = serializers.FloatField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    class Meta:
        model = Quiz
        fields = ('id','title','topic','category','difficulty','status','question_count','total_points','time_limit_seconds','time_limit_minutes','pass_percentage','is_ai_generated','language','created_by_username','tags','created_at')

class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    total_points = serializers.IntegerField(read_only=True)
    time_limit_minutes = serializers.FloatField(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    class Meta:
        model = Quiz
        fields = ('id','title','description','topic','category','difficulty','status','questions','question_count','total_points','time_limit_seconds','time_limit_minutes','pass_percentage','is_ai_generated','language','created_by_username','tags','created_at','updated_at')

class QuizCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ('title','description','topic','category','difficulty','time_limit_seconds','pass_percentage','tags','status','language')
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_id = serializers.IntegerField(required=False, allow_null=True)
    text_answer = serializers.CharField(required=False, allow_blank=True)

class AttemptResultSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_category = serializers.CharField(source='quiz.category', read_only=True)
    quiz_difficulty = serializers.CharField(source='quiz.difficulty', read_only=True)
    answers = serializers.SerializerMethodField()
    class Meta:
        model = QuizAttempt
        fields = ('id','quiz','quiz_title','quiz_category','quiz_difficulty','status','score','percentage','passed','time_taken_seconds','started_at','completed_at','answers')
    def get_answers(self, obj):
        result = []
        for a in obj.answers.select_related('question','selected_option'):
            correct_opt = a.question.options.filter(is_correct=True).first()
            result.append({
                'question_id': a.question_id,
                'question_text': a.question.question_text,
                'selected_option_id': a.selected_option_id,
                'selected_option_text': a.selected_option.option_text if a.selected_option else None,
                'is_correct': a.is_correct,
                'points_earned': a.points_earned,
                'question_points': a.question.points,
                'explanation': a.question.explanation,
                'correct_option': {'id': correct_opt.id, 'option_text': correct_opt.option_text} if correct_opt else None,
            })
        return result

class AttemptListSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    quiz_topic = serializers.CharField(source='quiz.topic', read_only=True)
    quiz_category = serializers.CharField(source='quiz.category', read_only=True)
    quiz_difficulty = serializers.CharField(source='quiz.difficulty', read_only=True)
    class Meta:
        model = QuizAttempt
        fields = ('id','quiz','quiz_title','quiz_topic','quiz_category','quiz_difficulty','status','score','percentage','passed','time_taken_seconds','started_at','completed_at')

class QuizGenerationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizGenerationRequest
        fields = ('id','topic','num_questions','difficulty','language','additional_instructions','status','generated_quiz','error_message','created_at','completed_at')
        read_only_fields = ('id','status','generated_quiz','error_message','created_at','completed_at')
    def validate_num_questions(self, v):
        if v < 1 or v > 20: raise serializers.ValidationError("Must be between 1 and 20.")
        return v
    def validate_topic(self, v):
        from .models import validate_topic
        valid, msg = validate_topic(v)
        if not valid: raise serializers.ValidationError(msg)
        return v

from rest_framework import generics, status, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from core.permissions import IsOwnerOrAdmin, IsAdminUser
from .models import Quiz, Question, QuizAttempt, UserAnswer, QuizGenerationRequest, CATEGORY_CHOICES
from .serializers import (QuizListSerializer, QuizDetailSerializer, QuizCreateSerializer,
    QuestionSerializer, AttemptListSerializer, AttemptResultSerializer,
    SubmitAnswerSerializer, QuizGenerationRequestSerializer)
from .ai_service import get_ai_service, AIQuizGenerationError, TopicValidationError
import logging
logger = logging.getLogger(__name__)

class QuizViewSet(ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['difficulty','status','is_ai_generated','category','language']
    search_fields = ['title','topic','description']
    ordering_fields = ['created_at','title','difficulty']
    def get_queryset(self):
        u = self.request.user
        if u.is_staff: return Quiz.objects.all().select_related('created_by')
        return Quiz.objects.filter(status='published').select_related('created_by')
    def get_serializer_class(self):
        if self.action == 'list': return QuizListSerializer
        if self.action in ('create','update','partial_update'): return QuizCreateSerializer
        return QuizDetailSerializer
    def get_permissions(self):
        if self.action in ('update','partial_update','destroy'): return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]
    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        quiz = s.save()
        return Response({'success':True,'data':QuizDetailSerializer(quiz).data}, status=201)
    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response({'success':True,'message':'Quiz deleted.'}, status=204)

class MyQuizzesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QuizListSerializer
    def get_queryset(self):
        ids = QuizAttempt.objects.filter(user=self.request.user).values_list('quiz_id',flat=True).distinct()
        return Quiz.objects.filter(id__in=ids, status='published').select_related('created_by').order_by('-created_at')

class QuizByCategoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        cat = request.query_params.get('category')
        if cat:
            qs = Quiz.objects.filter(status='published', category=cat).select_related('created_by')
            return Response({'success':True,'category':cat,'data':QuizListSerializer(qs,many=True).data})
        result = []
        for key, name in CATEGORY_CHOICES:
            count = Quiz.objects.filter(status='published', category=key).count()
            if count > 0: result.append({'key':key,'name':name,'quiz_count':count})
        return Response({'success':True,'data':result})

class QuizQuestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        qs = quiz.questions.prefetch_related('options').order_by('order')
        return Response({'success':True,'data':QuestionSerializer(qs,many=True).data})

class QuizAttemptView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id, status='published')
        existing = QuizAttempt.objects.filter(user=request.user, quiz=quiz, status='in_progress').first()
        if existing:
            return Response({'success':True,'message':'Resuming.','data':{'attempt_id':existing.id,'time_limit_seconds':quiz.time_limit_seconds,'started_at':existing.started_at}})
        attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)
        return Response({'success':True,'data':{'attempt_id':attempt.id,'quiz_id':quiz.id,'title':quiz.title,'category':quiz.category,'difficulty':quiz.difficulty,'time_limit_seconds':quiz.time_limit_seconds,'question_count':quiz.question_count,'total_points':quiz.total_points,'started_at':attempt.started_at}}, status=201)

class SubmitAnswerView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get_serializer(self, *args, **kwargs): return SubmitAnswerSerializer(*args, **kwargs)
    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user, status='in_progress')
        s = SubmitAnswerSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        question = get_object_or_404(attempt.quiz.questions, id=s.validated_data['question_id'])
        opt_id = s.validated_data.get('selected_option_id')
        data = {'text_answer': s.validated_data.get('text_answer','')}
        if opt_id:
            from .models import QuestionOption
            data['selected_option'] = get_object_or_404(QuestionOption, id=opt_id, question=question)
        answer, _ = UserAnswer.objects.update_or_create(attempt=attempt, question=question, defaults=data)
        return Response({'success':True,'data':{'question_id':question.id,'is_correct':answer.is_correct}})

class CompleteAttemptView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user, status='in_progress')
        with transaction.atomic():
            attempt.calculate_results()
            try:
                p = request.user.profile; p.update_stats(attempt.percentage); p.last_activity=timezone.now(); p.save()
            except: pass
        return Response({'success':True,'message':'Quiz completed!','data':AttemptResultSerializer(attempt).data})

class TimeoutAttemptView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user, status='in_progress')
        attempt.status = 'timed_out'
        attempt.calculate_results()
        return Response({'success':True,'message':'Time out.','data':AttemptResultSerializer(attempt).data})

class AttemptDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttemptResultSerializer
    def get_queryset(self):
        if self.request.user.is_staff: return QuizAttempt.objects.all()
        return QuizAttempt.objects.filter(user=self.request.user)

class UserAttemptHistoryView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttemptListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status','passed']
    def get_queryset(self):
        return QuizAttempt.objects.filter(user=self.request.user).select_related('quiz').order_by('-started_at')

class GenerateQuizView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get_serializer(self, *args, **kwargs): return QuizGenerationRequestSerializer(*args, **kwargs)
    def post(self, request):
        s = QuizGenerationRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        gen = QuizGenerationRequest.objects.create(user=request.user, **s.validated_data)
        try:
            gen.status='processing'; gen.save()
            ai = get_ai_service()
            result = ai.validate_and_generate(topic=gen.topic, num_questions=gen.num_questions, difficulty=gen.difficulty, language=gen.language, additional_instructions=gen.additional_instructions)
            qs_data = result['questions']
            with transaction.atomic():
                quiz = Quiz.objects.create(title=f"AI Quiz: {gen.topic.title()}", description=f"AI-generated quiz about {gen.topic}", topic=gen.topic, category=result['category'], difficulty=gen.difficulty, created_by=request.user, is_ai_generated=True, status='published', language=gen.language, time_limit_seconds=result['time_limit_seconds'])
                for i, qd in enumerate(qs_data):
                    q = Question.objects.create(quiz=quiz, question_text=qd['question'], explanation=qd.get('explanation',''), order=i+1, points=result['points_per_question'])
                    from .models import QuestionOption
                    for j, opt in enumerate(qd['options']):
                        QuestionOption.objects.create(question=q, option_text=opt['text'], is_correct=opt.get('is_correct',False), order=j)
                gen.status='completed'; gen.generated_quiz=quiz; gen.completed_at=timezone.now(); gen.save()
            return Response({'success':True,'message':f'Quiz generated with {len(qs_data)} questions!','data':{'quiz_id':quiz.id,'quiz_title':quiz.title,'category':result['category'],'difficulty':gen.difficulty,'points_per_question':result['points_per_question'],'time_limit_seconds':result['time_limit_seconds'],'question_count':len(qs_data)}}, status=201)
        except TopicValidationError as e:
            gen.status='failed'; gen.error_message=str(e); gen.save()
            return Response({'success':False,'message':str(e)}, status=400)
        except AIQuizGenerationError as e:
            gen.status='failed'; gen.error_message=str(e); gen.save()
            return Response({'success':False,'message':str(e)}, status=503)
        except Exception as e:
            logger.exception("Quiz generation error")
            gen.status='failed'; gen.error_message=str(e); gen.save()
            return Response({'success':False,'message':'An unexpected error occurred.'}, status=500)

class GenerationRequestListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QuizGenerationRequestSerializer
    def get_queryset(self): return QuizGenerationRequest.objects.filter(user=self.request.user).order_by('-created_at')

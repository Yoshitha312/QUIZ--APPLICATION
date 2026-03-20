from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Max, Sum, Q
from django.contrib.auth import get_user_model
from quizzes.models import Quiz, QuizAttempt, CATEGORY_CHOICES
from core.permissions import IsAdminUser
from .models import QuizAnalytics
User = get_user_model()

class UserDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        u = request.user
        attempts = QuizAttempt.objects.filter(user=u)
        completed = attempts.filter(status='completed')
        stats = completed.aggregate(avg_score=Avg('percentage'), best_score=Max('percentage'), total_time=Sum('time_taken_seconds'))
        cat_stats = completed.values('quiz__category').annotate(count=Count('id'), avg=Avg('percentage'), passed=Count('id', filter=Q(passed=True))).order_by('-count')
        recent = attempts.select_related('quiz').order_by('-started_at')[:5]
        return Response({'success':True,'data':{'summary':{'total_attempts':attempts.count(),'completed':completed.count(),'passed':completed.filter(passed=True).count(),'failed':completed.filter(passed=False).count(),'average_score':round(stats['avg_score'] or 0,2),'best_score':round(stats['best_score'] or 0,2),'total_time_minutes':round((stats['total_time'] or 0)/60,1)},'category_breakdown':[{'category':t['quiz__category'],'attempts':t['count'],'average_score':round(t['avg'] or 0,2),'passed':t['passed']} for t in cat_stats],'recent_attempts':[{'quiz_title':a.quiz.title,'topic':a.quiz.topic,'category':a.quiz.category,'difficulty':a.quiz.difficulty,'status':a.status,'percentage':a.percentage,'passed':a.passed,'date':a.started_at} for a in recent]}})

class QuizAnalyticsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        if not request.user.is_staff and quiz.created_by != request.user:
            return Response({'success':False,'message':'Permission denied.'}, status=403)
        analytics, _ = QuizAnalytics.objects.get_or_create(quiz=quiz)
        analytics.refresh_from_attempts()
        completed = QuizAttempt.objects.filter(quiz=quiz, status='completed')
        dist = {'0-20':0,'21-40':0,'41-60':0,'61-80':0,'81-100':0}
        for a in completed:
            p = a.percentage or 0
            if p<=20: dist['0-20']+=1
            elif p<=40: dist['21-40']+=1
            elif p<=60: dist['41-60']+=1
            elif p<=80: dist['61-80']+=1
            else: dist['81-100']+=1
        return Response({'success':True,'data':{'quiz_id':quiz.id,'quiz_title':quiz.title,'category':quiz.category,'difficulty':quiz.difficulty,'total_attempts':analytics.total_attempts,'completed_attempts':analytics.completed_attempts,'pass_rate':analytics.pass_rate,'average_score':round(analytics.average_score,2),'highest_score':round(analytics.highest_score,2),'score_distribution':dist}})

class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        cat = request.query_params.get('category')
        qs = QuizAttempt.objects.filter(status='completed')
        if cat: qs = qs.filter(quiz__category=cat)
        top = qs.values('user__username').annotate(best=Max('percentage'), attempts=Count('id'), avg=Avg('percentage'), passed=Count('id',filter=Q(passed=True)), total_score=Sum('score')).order_by('-best','-passed')[:20]
        cats = []
        for key, name in CATEGORY_CHOICES:
            cnt = QuizAttempt.objects.filter(status='completed', quiz__category=key).values('user').distinct().count()
            if cnt > 0: cats.append({'key':key,'name':name,'participants':cnt})
        return Response({'success':True,'category':cat,'categories':cats,'data':[{'rank':i+1,'username':e['user__username'],'best_score':round(e['best'],2),'average_score':round(e['avg'],2),'attempts':e['attempts'],'passed':e['passed'],'total_score':e['total_score']} for i,e in enumerate(top)]})

class AdminDashboardView(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        total_users=User.objects.count(); total_quizzes=Quiz.objects.count(); total_attempts=QuizAttempt.objects.count(); completed=QuizAttempt.objects.filter(status='completed').count()
        stats=QuizAttempt.objects.filter(status='completed').aggregate(avg=Avg('percentage'),passes=Count('id',filter=Q(passed=True)))
        popular=Quiz.objects.annotate(ac=Count('attempts')).order_by('-ac')[:5]
        top_users=User.objects.annotate(comp=Count('quiz_attempts',filter=Q(quiz_attempts__status='completed')),avg=Avg('quiz_attempts__percentage',filter=Q(quiz_attempts__status='completed'))).filter(comp__gt=0).order_by('-avg')[:5]
        return Response({'success':True,'data':{'overview':{'total_users':total_users,'total_quizzes':total_quizzes,'total_attempts':total_attempts,'completed':completed,'avg_score':round(stats['avg'] or 0,2),'pass_rate':round((stats['passes'] or 0)/completed*100 if completed else 0,2)},'popular_quizzes':[{'id':q.id,'title':q.title,'category':q.category,'attempts':q.ac} for q in popular],'top_performers':[{'username':u.username,'completed':u.comp,'avg_score':round(u.avg or 0,2)} for u in top_users]}})

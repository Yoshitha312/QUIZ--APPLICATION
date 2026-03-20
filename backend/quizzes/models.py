from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

CATEGORY_CHOICES = [
    ('programming','Programming'),('computer_science','Computer Science'),
    ('networking','Networking & Security'),('mathematics','Mathematics'),
    ('science','Science'),('geography','Geography'),('history','History'),
    ('general_knowledge','General Knowledge'),('language','Language & Literature'),
    ('economics','Economics & Business'),('other','Other'),
]
DIFFICULTY_POINTS = {'easy':1,'medium':2,'hard':3}
DIFFICULTY_TIMER = {'easy':600,'medium':900,'hard':1200}
INVALID_TOPICS = ['actors','actress','celebrities','gossip','movies list','songs list','actor list','actress list','film stars','bollywood gossip','personal life','dating','gambling','betting','adult','drugs']
CATEGORY_KEYWORDS = {
    'programming':['python','java','javascript','c++','c#','ruby','swift','kotlin','go','rust','coding','programming','algorithm','data structure','react','django','flask','nodejs','html','css','typescript'],
    'computer_science':['computer','software','hardware','operating system','machine learning','artificial intelligence','deep learning','data science','cloud','devops','database','sql','nosql','mongodb'],
    'networking':['network','cybersecurity','security','tcp','ip','protocol','firewall','vpn','encryption','hacking','wifi'],
    'mathematics':['math','calculus','algebra','geometry','statistics','trigonometry','probability','number theory','arithmetic'],
    'science':['physics','chemistry','biology','science','astronomy','geology','ecology','genetics','anatomy','botany','zoology'],
    'geography':['geography','country','capital','india','world','continent','ocean','river','mountain','tamil nadu','culture','state','map'],
    'history':['history','ancient','medieval','war','revolution','empire','civilization','dynasty','independence'],
    'economics':['economics','business','finance','accounting','management','marketing','trade','gdp','stock','investment','banking'],
    'language':['english','grammar','tamil','hindi','literature','vocabulary','language','writing','poetry'],
    'general_knowledge':['general','current affairs','gk','sports','olympics','environment','technology','quiz'],
}

def auto_categorize(topic):
    t = topic.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(kw in t for kw in kws): return cat
    return 'other'

def validate_topic(topic):
    t = topic.lower().strip()
    for inv in INVALID_TOPICS:
        if inv in t: return False, f"Topic '{topic}' is not suitable. Please choose an educational topic like Python, History, Geography, etc."
    if len(t) < 2: return False, "Topic is too short."
    return True, ""

class Quiz(models.Model):
    DIFF = [('easy','Easy'),('medium','Medium'),('hard','Hard')]
    STAT = [('draft','Draft'),('published','Published'),('archived','Archived')]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    topic = models.CharField(max_length=255)
    category = models.CharField(max_length=50,choices=CATEGORY_CHOICES,default='other')
    difficulty = models.CharField(max_length=10,choices=DIFF,default='medium')
    status = models.CharField(max_length=10,choices=STAT,default='published')
    created_by = models.ForeignKey(User,on_delete=models.CASCADE,related_name='created_quizzes')
    time_limit_seconds = models.IntegerField(default=900)
    pass_percentage = models.FloatField(default=60.0)
    is_ai_generated = models.BooleanField(default=False)
    language = models.CharField(max_length=20,default='english')
    tags = models.JSONField(default=list,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table='quizzes'; ordering=['-created_at']
    def __str__(self): return self.title
    @property
    def question_count(self): return self.questions.count()
    @property
    def total_points(self): return self.questions.aggregate(total=models.Sum('points'))['total'] or 0
    @property
    def time_limit_minutes(self): return round(self.time_limit_seconds/60,1)

class Question(models.Model):
    quiz = models.ForeignKey(Quiz,on_delete=models.CASCADE,related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20,default='mcq')
    points = models.IntegerField(default=1)
    explanation = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table='questions'; ordering=['order','id']

class QuestionOption(models.Model):
    question = models.ForeignKey(Question,on_delete=models.CASCADE,related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    class Meta:
        db_table='question_options'; ordering=['order']

class QuizAttempt(models.Model):
    STAT = [('in_progress','In Progress'),('completed','Completed'),('abandoned','Abandoned'),('timed_out','Timed Out')]
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz,on_delete=models.CASCADE,related_name='attempts')
    status = models.CharField(max_length=20,choices=STAT,default='in_progress')
    score = models.FloatField(null=True,blank=True)
    percentage = models.FloatField(null=True,blank=True)
    passed = models.BooleanField(null=True,blank=True)
    time_taken_seconds = models.IntegerField(null=True,blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True,blank=True)
    class Meta:
        db_table='quiz_attempts'; ordering=['-started_at']
    def calculate_results(self):
        from django.utils import timezone
        answers = self.answers.select_related('question','selected_option')
        total = self.quiz.total_points
        earned = sum(a.points_earned for a in answers if a.points_earned)
        self.score=earned; self.percentage=(earned/total*100) if total>0 else 0
        self.passed=self.percentage>=self.quiz.pass_percentage
        self.status='completed'; self.completed_at=timezone.now()
        if self.started_at: self.time_taken_seconds=int((self.completed_at-self.started_at).total_seconds())
        self.save(); return self

class UserAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt,on_delete=models.CASCADE,related_name='answers')
    question = models.ForeignKey(Question,on_delete=models.CASCADE,related_name='user_answers')
    selected_option = models.ForeignKey(QuestionOption,on_delete=models.SET_NULL,null=True,blank=True,related_name='user_answers')
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True,blank=True)
    points_earned = models.FloatField(default=0)
    answered_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table='user_answers'; unique_together=('attempt','question')
    def save(self,*args,**kwargs):
        if self.selected_option:
            self.is_correct=self.selected_option.is_correct
            self.points_earned=self.question.points if self.is_correct else 0
        super().save(*args,**kwargs)

class QuizGenerationRequest(models.Model):
    STAT=[('pending','Pending'),('processing','Processing'),('completed','Completed'),('failed','Failed')]
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='generation_requests')
    topic=models.CharField(max_length=255); num_questions=models.IntegerField(default=5)
    difficulty=models.CharField(max_length=10,default='medium'); language=models.CharField(max_length=20,default='english')
    additional_instructions=models.TextField(blank=True); status=models.CharField(max_length=20,choices=STAT,default='pending')
    generated_quiz=models.ForeignKey(Quiz,on_delete=models.SET_NULL,null=True,blank=True,related_name='generation_request')
    error_message=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True); completed_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        db_table='quiz_generation_requests'; ordering=['-created_at']

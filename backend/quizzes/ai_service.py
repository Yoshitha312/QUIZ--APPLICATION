import json, logging
from django.conf import settings
logger = logging.getLogger(__name__)

class AIQuizGenerationError(Exception): pass
class TopicValidationError(Exception): pass

LANGUAGE_PROMPTS = {
    'english':'Generate questions in English.',
    'tamil':'Generate questions in Tamil language (தமிழில் கேள்விகளை உருவாக்கவும்).',
    'hindi':'Generate questions in Hindi language.',
    'telugu':'Generate questions in Telugu language.',
    'kannada':'Generate questions in Kannada language.',
    'malayalam':'Generate questions in Malayalam language.',
}

class GroqService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = "llama-3.3-70b-versatile"

    def validate_and_generate(self, topic, num_questions, difficulty, language='english', additional_instructions=''):
        from .models import validate_topic, auto_categorize, DIFFICULTY_POINTS, DIFFICULTY_TIMER
        valid, msg = validate_topic(topic)
        if not valid: raise TopicValidationError(msg)
        category = auto_categorize(topic)
        pts = DIFFICULTY_POINTS.get(difficulty, 1)
        timer = DIFFICULTY_TIMER.get(difficulty, 900)
        questions = self.generate_quiz_questions(topic, num_questions, difficulty, language, additional_instructions)
        return {'questions': questions, 'category': category, 'points_per_question': pts, 'time_limit_seconds': timer}

    def generate_quiz_questions(self, topic, num_questions, difficulty, language='english', additional_instructions=''):
        if not self.api_key:
            return self._fallback(topic, num_questions)
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            diff_desc = {'easy':'basic introductory level','medium':'intermediate level','hard':'advanced level'}.get(difficulty,'medium')
            lang = LANGUAGE_PROMPTS.get(language, LANGUAGE_PROMPTS['english'])
            extra = f"\nAdditional: {additional_instructions}" if additional_instructions else ""
            prompt = f"""Generate exactly {num_questions} MCQ questions about "{topic}". Difficulty: {diff_desc}. {lang}{extra}
IMPORTANT: Only educational content. Return ONLY a JSON array:
[{{"question":"Q?","options":[{{"text":"Correct","is_correct":true}},{{"text":"Wrong A","is_correct":false}},{{"text":"Wrong B","is_correct":false}},{{"text":"Wrong C","is_correct":false}}],"explanation":"Brief explanation."}}]
Rules: 4 options, exactly 1 is_correct:true, return ONLY the JSON array."""
            resp = client.chat.completions.create(model=self.model, messages=[{"role":"user","content":prompt}], temperature=0.7, max_tokens=4000)
            return self._parse(resp.choices[0].message.content)
        except AIQuizGenerationError: raise
        except Exception as e:
            logger.error(f"Groq error: {e}")
            raise AIQuizGenerationError(f"AI service error: {str(e)}")

    def _parse(self, text):
        text = text.strip()
        if "```" in text:
            text = '\n'.join(l for l in text.split('\n') if not l.strip().startswith('```')).strip()
        try: qs = json.loads(text)
        except:
            import re
            m = re.search(r'\[.*\]', text, re.DOTALL)
            if m:
                try: qs = json.loads(m.group())
                except: raise AIQuizGenerationError("Could not parse AI response.")
            else: raise AIQuizGenerationError("Could not parse AI response.")
        if not isinstance(qs, list): raise AIQuizGenerationError("Not a list.")
        valid = [q for q in qs if all(k in q for k in ('question','options','explanation')) and len(q['options'])>=2 and sum(1 for o in q['options'] if o.get('is_correct'))==1]
        if not valid: raise AIQuizGenerationError("No valid questions.")
        return valid

    def _fallback(self, topic, n):
        return [{"question":f"Sample Q{i+1} about {topic}?","options":[{"text":"Correct answer","is_correct":True},{"text":"Wrong A","is_correct":False},{"text":"Wrong B","is_correct":False},{"text":"Wrong C","is_correct":False}],"explanation":f"Sample explanation {i+1}."} for i in range(n)]

def get_ai_service(): return GroqService()

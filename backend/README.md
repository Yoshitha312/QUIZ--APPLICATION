# AI-Powered Quiz API

A comprehensive REST API for a quiz application built with Django, Django REST Framework, and PostgreSQL. Features user authentication, AI-powered quiz generation (Google Gemini), attempt management, and detailed analytics.

---

##  Local Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis (optional, for caching)

### Step 1 — Clone & Create Virtual Environment
```bash
git clone <your-repo-url>
cd quiz_api
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### Step 2 — Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Configure Environment
```bash
cp .env.example .env
# Now edit .env with your values
```

**.env values to set:**
| Key | Description |
|-----|-------------|
| `SECRET_KEY` | Any long random string |
| `DB_NAME` | Your PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Usually `localhost` |
| `GEMINI_API_KEY` | Free key from https://aistudio.google.com/app/apikey |
| `REDIS_URL` | Optional — remove from settings if not using Redis |

### Step 4 — Create PostgreSQL Database
```bash
psql -U postgres
CREATE DATABASE quiz_db;
\q
```

### Step 5 — Run Migrations
```bash
python manage.py migrate
```

### Step 6 — Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### Step 7 — Start Development Server
```bash
python manage.py runserver
```

The API is now running at: **http://127.0.0.1:8000**

**Note on Redis:** If you don't have Redis, edit `quiz_app/settings.py` and replace the `CACHES` block with:
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
```
Also remove `django-redis` and `redis` from `requirements.txt` and uninstall them.

---

## API Documentation

Visit **http://127.0.0.1:8000/api/docs/** for interactive Swagger UI.

---

## Database Schema & Model Relationships

```
User (AbstractUser)
 ├── role: student | teacher | admin
 └── UserProfile (1:1)
      └── stats: total_quizzes, avg_score, best_score, streak

Quiz
 ├── created_by → User (FK)
 ├── questions → Question[]
 │    └── options → QuestionOption[]
 ├── attempts → QuizAttempt[]
 └── analytics → QuizAnalytics (1:1)

QuizAttempt
 ├── user → User (FK)
 ├── quiz → Quiz (FK)
 └── answers → UserAnswer[]
      ├── question → Question (FK)
      └── selected_option → QuestionOption (FK)

QuizGenerationRequest
 ├── user → User (FK)
 └── generated_quiz → Quiz (FK, nullable)
```

---

##  API Endpoint Overview

### Auth (`/api/v1/auth/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register/` | Register new user |
| POST | `/login/` | Login (returns JWT tokens) |
| POST | `/logout/` | Logout (blacklist refresh token) |
| POST | `/token/refresh/` | Refresh access token |
| GET/PATCH | `/profile/` | Get or update own profile |
| PUT | `/change-password/` | Change password |
| GET | `/users/` | List all users (admin only) |

### Quizzes (`/api/v1/quizzes/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List published quizzes (filterable) |
| POST | `/` | Create quiz |
| GET | `/{id}/` | Get quiz detail with questions |
| PATCH | `/{id}/` | Update quiz (owner/admin) |
| DELETE | `/{id}/` | Delete quiz (owner/admin) |
| GET/POST | `/{id}/questions/` | List or add questions |
| POST | `/{id}/attempt/` | Start a quiz attempt |
| POST | `/attempts/{id}/answer/` | Submit an answer |
| POST | `/attempts/{id}/complete/` | Complete attempt & get results |
| GET | `/attempts/{id}/` | Get attempt detail with results |
| GET | `/my-attempts/` | User's attempt history |
| POST | `/generate/` | Generate quiz with AI |
| GET | `/generation-requests/` | AI generation request history |
| GET | `/admin/all/` | All quizzes (admin only) |

### Analytics (`/api/v1/analytics/`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/` | Personal performance dashboard |
| GET | `/quiz/{id}/` | Analytics for a specific quiz |
| GET | `/admin/dashboard/` | Platform-wide admin analytics |
| GET | `/leaderboard/` | Top performers leaderboard |

---

## Authentication

All endpoints (except register/login) require a Bearer JWT token:

```
Authorization: Bearer <access_token>
```

Tokens are obtained from `/api/v1/auth/login/` and refreshed via `/api/v1/auth/token/refresh/`.

---

##  AI Integration

**Provider:** Google Gemini 1.5 Flash (free tier)

**How it works:**
1. User sends POST to `/api/v1/quizzes/generate/` with `topic`, `num_questions` (1–20), `difficulty`
2. API creates a `QuizGenerationRequest` record
3. A structured prompt is sent to Gemini API requesting a JSON array of questions
4. The response is parsed and validated (correct option count, format checks)
5. A `Quiz` and its `Question`/`QuestionOption` records are created atomically
6. The generation request is marked complete with a reference to the new quiz

**Fallback:** If no API key is configured, the system returns sample placeholder questions so you can test the full flow without a key.

**Error handling:**
- Timeout → 503 with retry message
- Bad JSON from AI → re-attempts extraction with regex
- Invalid question structure → filtered out, remaining questions used
- Complete failure → generation request marked `failed`, error stored

---

##  Design Decisions & Trade-offs

### Authentication
- **JWT over Session:** Stateless, works well for API clients and mobile apps
- **SimpleJWT** with token blacklisting on logout for security
- **Role-based:** `student`, `teacher`, `admin` roles with permissions enforced at view level

### Data Modeling
- `UserAnswer.save()` auto-calculates correctness and points — keeps scoring logic in the model layer
- `QuizAttempt.calculate_results()` is atomic and computes everything in one call
- `QuizAnalytics` is a denormalized summary table refreshed on demand — avoids expensive aggregations on every request
- `JSONField` for quiz tags — flexible without a separate join table

### API Design
- ViewSet for quizzes (standard CRUD) + dedicated APIViews for complex operations (attempts, AI generation)
- Separate serializers for list vs detail — avoids N+1 on list views
- `select_related` / `prefetch_related` everywhere to prevent query bloat

### Caching
- Quiz list responses cached in Redis for 5 minutes
- Cache invalidated on quiz create/update/delete
- Falls back to in-memory cache if Redis unavailable

### Pagination
- All list endpoints paginated (default 10, max 100 per page)
- Response includes `count`, `total_pages`, `next`, `previous`

### Performance
- Database indexes on frequent filter fields: `topic`, `difficulty`, `status`, `user+quiz`
- `unique_together` on `UserAnswer(attempt, question)` prevents duplicate answers
- Throttling: 100/day anonymous, 1000/day authenticated users

---

##  Testing Approach

To test manually with curl or Postman:

```bash
# 1. Register
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@test.com","password":"Pass1234!","password2":"Pass1234!"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"Pass1234!"}'

# 3. Generate AI Quiz (use token from step 2)
curl -X POST http://localhost:8000/api/v1/quizzes/generate/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"topic":"Python programming","num_questions":5,"difficulty":"medium"}'

# 4. Start attempt
curl -X POST http://localhost:8000/api/v1/quizzes/<quiz_id>/attempt/ \
  -H "Authorization: Bearer <access_token>"

# 5. Submit answer
curl -X POST http://localhost:8000/api/v1/quizzes/attempts/<attempt_id>/answer/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"question_id": 1, "selected_option_id": 2}'

# 6. Complete quiz
curl -X POST http://localhost:8000/api/v1/quizzes/attempts/<attempt_id>/complete/ \
  -H "Authorization: Bearer <access_token>"
```

---

##  Deployment (Railway)

1. Push to GitHub
2. Create new project on [railway.app](https://railway.app)
3. Add PostgreSQL and Redis plugins
4. Set environment variables from `.env.example`
5. Set `DEBUG=False`, `ALLOWED_HOSTS=your-app.railway.app`
6. Deploy — Railway auto-detects `Procfile`

---

## Project Structure

```
quiz_api/
├── quiz_app/           # Django project settings & URLs
├── users/              # User model, auth, profiles
├── quizzes/            # Quiz, Question, Attempt models + AI service
├── analytics/          # Analytics & leaderboard
├── core/               # Shared: pagination, permissions, exceptions
├── manage.py
├── requirements.txt
├── Procfile
├── runtime.txt
└── .env.example
```

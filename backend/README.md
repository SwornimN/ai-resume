# Resume-to-Job Matcher

A REST API that scores how well a candidate's resume matches a job posting, using Claude for structured extraction and comparison. Built as a backend portfolio project to demonstrate relational data modeling, JWT authentication, file handling, and integrating an external AI API into a production-style FastAPI service.

## What it does

A user signs up, uploads a resume (PDF), and pastes in one or more job postings. The API extracts structured data from both (skills, years of experience, education, keywords) via Claude, then on request compares a resume against a job posting and returns a match score, the overlapping skills, the gaps, and a few sentences of actionable feedback.

## Why this isn't just CRUD

A few decisions in this project are there on purpose, not by default:

**AI calls can fail, but user data shouldn't.** If the Claude call for structured extraction errors out — bad network, malformed response, rate limit — the resume or job posting is still saved, just with `parsed_json` left as `null` instead of the whole request 500ing. Matching against an unparsed record returns a clean `400` instead of crashing.

**Ownership is enforced at the query level, not just the route level.** Every read or write to a resume, job posting, or match is filtered by the authenticated user's ID in the database query itself, not checked after the fact — so there's no path where one user can see or act on another user's data.

**Auth doesn't lean on a deprecated stack.** Password hashing uses `bcrypt` directly (`hashpw` / `checkpw`) instead of `passlib`'s `CryptContext`, since recent `bcrypt` releases broke passlib's backend for it. JWTs are signed and verified with `python-jose`.

## Tech stack

| Layer | Choice |
|---|---|
| Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL |
| Auth | JWT (python-jose) + bcrypt |
| PDF parsing | pypdf |
| AI | Anthropic API (Claude Sonnet 4.6) |
| Validation | Pydantic v2 |

## Project structure

```
backend/
├── main.py                      # App entry point, router registration, table creation
├── requirements.txt
├── .env.example
└── app/
    ├── config.py                 # Settings loaded from .env
    ├── database.py                # Engine, session, declarative base
    ├── models.py                  # User, Resume, JobPosting, Match
    ├── schemas.py                 # Request/response models
    ├── auth.py                    # Hashing, JWT issuance, current-user dependency
    ├── routers/
    │   ├── auth_router.py         # /auth/signup, /auth/login
    │   ├── resumes_router.py      # /resumes
    │   ├── job_postings_router.py # /job-postings
    │   └── matches_router.py      # /matches
    └── services/
        ├── ai_service.py          # Claude calls: extraction + comparison
        └── pdf_service.py         # PDF → plain text
```

## API reference

| Method | Path | Auth required | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | No | Create an account |
| `POST` | `/auth/login` | No | Exchange credentials for a JWT |
| `POST` | `/resumes` | Yes | Upload a PDF resume |
| `GET` | `/resumes` | Yes | List your resumes |
| `POST` | `/job-postings` | Yes | Add a job posting |
| `GET` | `/job-postings` | Yes | List your job postings |
| `POST` | `/matches` | Yes | Score a resume against a job posting |
| `GET` | `/matches` | Yes | List your matches |
| `GET` | `/matches/{id}` | Yes | Fetch a single match |

Full interactive docs (Swagger UI) are served at `/docs` once the app is running — you can authenticate and try every endpoint from the browser without writing a single request by hand.

## Getting started

### Prerequisites

- Python 3.11+ (tested through 3.14)
- PostgreSQL, running locally or reachable remotely
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

### 1. Set up the virtual environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

> **Note on very new Python versions:** if pip tries to *build* `psycopg2-binary` or `pydantic-core` from source instead of downloading a prebuilt wheel, it means your Python version is newer than the pinned package versions have wheels for. Bump those two packages to their latest release in `requirements.txt` and reinstall — no compiler toolchain required.

### 3. Create the database

```powershell
psql -U postgres -c "CREATE DATABASE resume_matcher;"
```

(If `psql` isn't recognized, add PostgreSQL's `bin` folder, e.g. `C:\Program Files\PostgreSQL\18\bin`, to your PATH and open a fresh terminal.)

### 4. Configure environment variables

```powershell
Copy-Item .env.example .env
```

Fill in `.env`:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/resume_matcher
JWT_SECRET_KEY=use-a-long-random-string-here
ANTHROPIC_API_KEY=sk-ant-...
```

Generate a secret key with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run it

```powershell
uvicorn main:app --reload
```

Tables are created automatically on first startup. Visit `http://localhost:8000/docs` for the interactive API explorer.

## Example requests

### PowerShell

```powershell
# Sign up
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/signup" `
  -ContentType "application/json" `
  -Body '{"email":"alice@example.com","password":"secret123"}'

# Log in
$login = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/login" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{ username = "alice@example.com"; password = "secret123" }
$headers = @{ Authorization = "Bearer $($login.access_token)" }

# Upload a resume
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/resumes" `
  -Headers $headers -Form @{ file = Get-Item ".\resume.pdf" }

# Add a job posting
$job = @{
  title    = "Backend Engineer"
  company  = "Acme Corp"
  raw_text = "Looking for a Python developer with FastAPI and PostgreSQL experience..."
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/job-postings" `
  -Headers $headers -ContentType "application/json" -Body $job

# Create a match
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/matches" `
  -Headers $headers -ContentType "application/json" `
  -Body '{"resume_id":1,"job_posting_id":1}'
```

### curl

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"secret123"}'

TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=alice@example.com&password=secret123" | jq -r .access_token)

curl -X POST http://localhost:8000/resumes \
  -H "Authorization: Bearer $TOKEN" -F "file=@resume.pdf"

curl -X POST http://localhost:8000/job-postings \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Backend Engineer","company":"Acme Corp","raw_text":"..."}'

curl -X POST http://localhost:8000/matches \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"resume_id":1,"job_posting_id":1}'
```

## Possible extensions

- Swap `Base.metadata.create_all()` for Alembic migrations once the schema needs to evolve post-launch.
- Add a retry/re-parse endpoint for resumes or job postings stuck with `parsed_json = null`.
- Rate-limit the AI-calling endpoints to control Anthropic API spend.
- Add pagination to the list endpoints once a user has more than a handful of records.

## License

MIT — feel free to use this as a reference for your own projects.

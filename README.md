# Job Tracker API (Django)

![CI](https://github.com/YOUR-USERNAME/job-tracker-django/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/Django-6.1-092E20)
![DRF](https://img.shields.io/badge/DRF-3.18-A30000)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)

A REST API for tracking job applications, built with **Django**, **Django REST Framework** and **PostgreSQL**.
Users sign up, add the companies they're interested in, and move each application through its pipeline
(wishlist → applied → interviewing → offer / rejected), with search, filtering, ordering and summary stats.

**Live demo:** _add your Render URL here_ · **Swagger docs:** `/api/docs/` · **Admin:** `/admin/`

## Highlights

- **JWT authentication** with access and refresh tokens (`djangorestframework-simplejwt`)
- **Custom user model** that logs in with email, with Django's password validators enforced at registration
- **Per-user data isolation** in one reusable mixin: other users' records return 404, not 403, so IDs can't be probed
- **Data integrity at two levels**: serializer validation for clear API errors, plus database constraints
  (unique company name per user, `salary_min <= salary_max`) so bad data can't get in another way
- **Filtering, search, ordering and pagination** via `django-filter` and DRF, with a custom ordering filter that keeps
  empty values last
- **Stats endpoint** computed with a single `GROUP BY` query
- **Django admin** configured with search, filters, inline applications and editable status
- **OpenAPI docs** generated with `drf-spectacular` (Swagger UI and ReDoc)
- **27 tests** run against Postgres in GitHub Actions, alongside linting, `check --deploy`, migration drift and schema validation
- **Production-ready setup**: Gunicorn, WhiteNoise, environment-based settings, Docker, and a Render blueprint

## Data model

```mermaid
erDiagram
    USER ||--o{ COMPANY : owns
    USER ||--o{ APPLICATION : owns
    COMPANY ||--o{ APPLICATION : receives
    USER {
        bigint id PK
        string email UK
        string password
        string full_name
        datetime date_joined
    }
    COMPANY {
        bigint id PK
        bigint owner_id FK
        string name "unique per owner"
        string website
        string industry
        string location
    }
    APPLICATION {
        bigint id PK
        bigint owner_id FK
        bigint company_id FK
        string role_title
        string status "wishlist, applied, interviewing, offer, rejected, withdrawn"
        int salary_min "check: <= salary_max"
        int salary_max
        date applied_on
        text notes
    }
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/register/` | Create an account |
| `POST` | `/api/auth/token/` | Get access and refresh tokens (`email`, `password`) |
| `POST` | `/api/auth/token/refresh/` | Get a new access token |
| `GET` / `PATCH` | `/api/auth/me/` | View or update your profile |
| `GET` / `POST` | `/api/companies/` | List (`search`, `industry`, `ordering`) or create companies |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/companies/{id}/` | Company detail |
| `GET` / `POST` | `/api/applications/` | List or create applications |
| `GET` | `/api/applications/stats/` | Counts by status and response rate |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/applications/{id}/` | Application detail |
| `GET` | `/health/` | Liveness and database check |

Application list parameters: `status`, `company`, `applied_after`, `applied_before`, `min_salary`, `search`
(role, notes and company name), `ordering` (`created_at`, `applied_on`, `role_title`, `salary_max`, prefix `-` for
descending), `limit`, `offset`.

### Example

```bash
# Register and get a token
curl -X POST localhost:8000/api/auth/register/ -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"A-strong-password-1"}'
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token/ -H "Content-Type: application/json" \
  -d '{"email":"me@example.com","password":"A-strong-password-1"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

# Add a company and an application
curl -X POST localhost:8000/api/companies/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{"name":"Acme","website":"https://acme.com"}'
curl -X POST localhost:8000/api/applications/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id":1,"role_title":"Backend Engineer","status":"applied","salary_min":100000,"salary_max":130000}'

# Highest-paying applications you've submitted
curl "localhost:8000/api/applications/?status=applied&ordering=-salary_max" -H "Authorization: Bearer $TOKEN"
```

## Running locally

### Option 1: Docker (easiest)

```bash
docker compose up --build
docker compose exec web python manage.py seed_demo         # optional demo data
docker compose exec web python manage.py createsuperuser   # for /admin
```

Open http://localhost:8000/api/docs/. The demo login is `demo@example.com` / `Demo-password-2026`.

### Option 2: Virtual environment

Requires Python 3.12+. Uses SQLite unless you set `DATABASE_URL`.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_demo          # optional demo data
python manage.py createsuperuser    # optional, for /admin
python manage.py runserver
```

To use PostgreSQL instead, export `DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/job_tracker` first.

## Tests and code quality

```bash
python manage.py test                       # SQLite by default; set DATABASE_URL to test on Postgres
ruff check . && ruff format --check .
python manage.py makemigrations --check     # fails if models changed without a migration
```

CI (`.github/workflows/ci.yml`) runs all of these against Postgres 16, plus `manage.py check --deploy` with
production settings and OpenAPI schema validation.

## Deploying for free

1. Create a free Postgres database on [Neon](https://neon.tech) or [Supabase](https://supabase.com) and copy its connection string.
2. On [Render](https://render.com), choose **New → Blueprint** and select this repository. It reads `render.yaml`.
3. Set `DATABASE_URL` when prompted. `DJANGO_SECRET_KEY` is generated for you, and `DEBUG` is off.
4. When the deploy finishes, open `https://<your-service>.onrender.com/api/docs/`.
5. Optional: in the Render shell, run `python manage.py seed_demo` and `python manage.py createsuperuser`.

Render's free web services sleep after about 15 minutes without traffic, so the first request after a pause is slower.

## Project structure

```
config/                Project settings, root URLs, WSGI
accounts/              Custom email-based User model, registration, JWT and profile endpoints
tracker/
  models.py            Company and Application, with database constraints
  serializers.py       Validation and nested company summaries
  views.py             ViewSets, ownership mixin, stats action
  filters.py           FilterSet and nulls-last ordering
  admin.py             Admin configuration
  management/commands/seed_demo.py   Demo data loader
  tests.py             API tests
```

## Design decisions

- **Ownership in one mixin.** `OwnedQuerysetMixin` filters every queryset by the current user and sets the owner on
  create, so no view can accidentally leak or misassign data.
- **Company choices scoped per request.** The application serializer limits `company_id` to the user's own companies,
  so attaching an application to someone else's company is a validation error.
- **Validation in the API and the database.** Serializers give readable errors; `UniqueConstraint` and
  `CheckConstraint` guarantee the rules even for data written through the admin or a shell.
- **`select_related` and annotated counts** keep list endpoints to a single query each.
- **Settings from environment variables**, with SQLite as a zero-setup default and Postgres everywhere else.

## Possible next steps

- Interview events with dates and reminder emails (Celery)
- Token blacklisting on logout
- A React or HTMX front end that uses this API

## License

MIT, see [LICENSE](LICENSE).

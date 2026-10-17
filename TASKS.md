# Barabanki Connect — Task Tracker

## Phase 0: Architecture, Inspection & Plan
- [x] Inspect existing directory, virtual environment, and packages
- [x] Verify PostgreSQL service availability on system (PostgreSQL 18 running)
- [x] Create ROADMAP.md
- [x] Create PROJECT_STRUCTURE.md
- [x] Create TASKS.md
- [x] Create CHANGELOG.md
- [x] Create README.md

## Phase 1: Project Foundation & Configuration
- [x] Initialize Git repository (Done with `git init`)
- [x] Create `.gitignore` for Python, Windows, Virtual Environments, IDE, and Secrets
- [x] Create `.env.example` with documented environment variables
- [x] Create `.env` for local execution with safe development defaults
- [x] Create `requirements.txt` with FastAPI, SQLAlchemy, Alembic, Jinja2, Uvicorn, bcrypt, jose, etc.
- [x] Install dependencies into virtualenv and verify importability
- [x] Implement `app/core/config.py` for settings management via pydantic-settings
- [x] Implement `app/core/database.py` with SQLAlchemy engine, session maker, and Declarative Base
- [x] Implement `app/core/security.py` with bcrypt password hashing, token generation, and verification
- [x] Implement `app/core/dependencies.py` with DB session management and current user resolution

## Phase 2: Responsive UI Design & Reusable Components
- [x] Create design tokens and stylesheet `app/static/css/style.css`
  - Color palette (Barabanki Heritage: saffron/amber accent #D97706, deep navy #1E3A8A, teal #0D9488, slate neutrals)
  - Full Dark Mode support via CSS custom properties and `data-theme` attribute
  - Typography, spacing scale, grid/flex utilities
  - Reusable components: Buttons, cards, badges, alerts, modals, tables, forms, hero sections, stats counters
- [x] Create client-side JavaScript `app/static/js/main.js`
  - Theme toggler (light/dark with localStorage sync)
  - Mobile drawer navigation toggling & overlay
  - Dynamic Toast / Flash notification alerts
  - Client-side form helpers & CSRF token inclusion
- [x] Create Leaflet map helper `app/static/js/map.js` for OpenStreetMap integration
- [x] Create Chart.js helper `app/static/js/admin_charts.js` for admin dashboards
- [x] Create SVG placeholder asset `app/static/images/placeholder.svg`

## Phase 3: PostgreSQL Database Models & Authentication
- [x] Build SQLAlchemy 2.0 ORM models in `app/models/`:
  - `User`: Roles (admin, moderator, business_owner, creator, resident), status, bio, timestamps
  - `NewsArticle`: Title, slug, content, summary, category, source_attribution, status, views
  - `Event`: Title, slug, description, category, dates, venue, coordinates, organizer info
  - `Business`: Name, slug, category, address, locality, coordinates, phone, verified flag, rating
  - `JobListing`: Title, company, job_type, salary, description, requirements, status
  - `EducationInstitute`: Name, category (school, college, coaching), courses, address, contact
  - `CommunityPost` & `Comment`: Title, category, content, upvotes, moderation flags
  - `Report`: Target type, target id, reason, status, reporting user
  - `ContactMessage`: Name, email, subject, message, read flag
  - `CreatorProfile`: Craft category, portfolio link, bio, socials, featured status
  - `TourismSpot`: Landmark name, history, category, address, coordinates, visitor info
- [x] Implement authentication workflow:
  - Password hashing with bcrypt
  - Cookie session authentication & JWT Bearer token support
  - Role-based authorization dependencies (`require_auth`, `require_admin`, `require_moderator`)
  - User registration, login, logout, and profile endpoints
- [x] Create seed data script `app/seeds/seed_data.py`:
  - Authentic Barabanki civic, historical, and educational records
  - Deva Sharif, Parijaat Tree, Lodheshwar Mahadev, Handloom weaving clusters
  - Government and private colleges, hospitals, and local market hubs
  - Default administrative and demo accounts

## Phase 4: Main Website Pages & Navigation
- [x] Master template `app/templates/base.html`
- [x] Component templates: `navbar.html`, `footer.html`, `alerts.html`, `pagination.html`
- [x] Home page `app/templates/pages/index.html` with hero, highlights, quick links, news, events, jobs
- [x] About page `app/templates/pages/about.html` highlighting district history and mission
- [x] Contact & Helplines page `app/templates/pages/contact.html` with emergency services and inquiry form
- [x] Heritage & Tourism page `app/templates/tourism/list.html` and `detail.html` with interactive Leaflet map
- [x] Legal pages: Privacy Policy (`privacy.html`) and Terms of Service (`terms.html`)

## Phase 5: Backend APIs & CRUD Operations
- [x] Implement REST API routers under `/api/v1/`:
  - Auth, News, Events, Businesses, Jobs, Education, Community, Tourism, Creators, Contact, Search
- [x] Implement server-rendered web routers with seamless form handling and redirection
- [x] Universal Search endpoint with cross-entity searching and filtering

## Phase 6: Core Domain Modules
- [x] Local News Module (category filtering, reader view, source attribution, admin post)
- [x] Events Module (date filters, interactive map view, event detail, organizer contacts)
- [x] Business Directory (locality filter, category tabs, contact phone/email, verification badge)
- [x] Jobs Portal (job type tags, salary range, application workflow, employer posting)
- [x] Education & Skills Hub (institutes directory, course info, admission links)
- [x] Community Forum (post creation, comment threads, upvotes, report button)
- [x] Creators Showcase (artisan and creator cards, portfolio links)

## Phase 7: Admin Dashboard, Moderation & Security
- [x] Admin Dashboard UI (`/admin`) with metric KPI cards
- [x] Chart.js integration for user activity, module distribution, and registration trends
- [x] Content moderation queue (resolve or dismiss flagged items)
- [x] Verification and approval queue for submitted businesses and job listings
- [x] User role management (promoting users, suspending accounts)
- [x] Security hardening (CSRF protection, XSS escaping, rate-limiting headers, secure cookies)

## Phase 8: Testing, QA & Bug Fixing
- [x] Write test configuration in `tests/conftest.py` with test database
- [x] Write unit tests for password hashing and security
- [x] Write integration tests for authentication (register, login, invalid credentials)
- [x] Write route tests for public web pages (Home, News, Events, Businesses, Jobs, Education, Tourism)
- [x] Write API CRUD tests
- [x] Execute `pytest -v` and ensure 100% test pass rate (43 of 43 passed)
- [x] Perform live HTTP checks with FastAPI application runner

## Phase 9: Deployment Preparation & Finalization
- [x] Create `Dockerfile` with multi-stage build or slim Python 3.12 image
- [x] Create `docker-compose.yml` for unified local/production orchestration
- [x] Configure Alembic migrations (`alembic.ini`, `alembic/env.py`, initial revision autogenerated and applied)
- [x] Create database migration / init command script (`init_db.py` / `app.seeds.seed_data`)
- [x] Update documentation (`README.md`, `CHANGELOG.md`) with final run steps

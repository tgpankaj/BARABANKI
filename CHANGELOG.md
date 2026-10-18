# Changelog — Barabanki Connect

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-10-18

### Cleaned & Audited
- **Phase 5 Codebase Audit & Refactoring**:
  - Established dedicated Git branch `phase-5-audit-cleanup` preserving all existing working tree modifications.
  - Performed static code analysis and eliminated all unused imports (`F401`), unused variables (`F841`), and undefined symbols (`F821`) across all models, routers, schemas, scripts, and tests.
  - Consolidated duplicate response imports in `app/routers/auth.py`.
  - Audited all 48 HTML templates: verified that every single template is actively referenced, verified all form actions match registered FastAPI routes, and resolved in-page navigation anchors in `education/list.html`.
  - Audited static images and JavaScript files: verified that all static assets referenced in templates exist on disk.
  - Updated `docker-compose.yml` PostgreSQL data volume path to standard `/var/lib/postgresql/data` and removed obsolete backup file `docker-compose.yml.bak`.
  - Hardened `.gitignore` to comprehensively ignore backup directories (`backups/`), database files (`*.db`), and temporary files (`*.bak`, `*.old`, `*.tmp`, `*~`).
  - Verified 100% test pass rate across all 85 tests (7 test modules, 0 failures, 0 warnings).

## [1.0.0] - 2026-10-17

### Added
- Phase 0: Complete architectural design, repository initialization, and project documentation (`ROADMAP.md`, `PROJECT_STRUCTURE.md`, `TASKS.md`, `CHANGELOG.md`, `README.md`).
- Phase 1: Environment configuration (`.env.example`, `.env`), `.gitignore`, requirements definitions, and core application modules (`app/core/config.py`, `app/core/database.py`, `app/core/security.py`, `app/core/dependencies.py`).
- Phase 2: Design system stylesheet (`app/static/css/style.css`) with Barabanki civic palette, full dark mode, and responsive layout utilities. Client JavaScript (`app/static/js/main.js`, `map.js`, `admin_charts.js`).
- Phase 3: SQLAlchemy 2.0 relational models across 11 domains (User, NewsArticle, Event, Business, JobListing, EducationInstitute, CommunityPost, Comment, Report, ContactMessage, CreatorProfile, TourismSpot). Secure authentication system with bcrypt hashing, session cookies, and JWT token support. Authentic Barabanki seed data generator (`app/seeds/seed_data.py`).
- Phase 4: Jinja2 master templates (`base.html`), navigation components (`navbar.html`, `footer.html`, `alerts.html`, `pagination.html`), and public web pages (Home, About, Contact, Tourism & Heritage with Leaflet map, Terms, Privacy).
- Phase 5 & 6: Feature modules (News, Events, Business Directory, Jobs Portal, Education Hub, Community Forum, Creators Showcase, Universal Search) with dual web-routing and JSON REST API endpoints.
- Phase 7: Admin portal (`/admin`) with Chart.js analytics, content moderation queue, verification workflow for business and job submissions, user role management, and security hardening.
- Phase 8: Automated test suite with `pytest` covering authentication, routes, API endpoints, and models with 100% passing tests.
- Phase 9: Containerization configurations (`Dockerfile`, `docker-compose.yml`) and production-ready startup scripts.

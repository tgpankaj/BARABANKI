# Barabanki Connect — Project Roadmap

**Version:** 1.0.0  
**Target:** Production-Ready Community & Civic Web Application for Barabanki, Uttar Pradesh, India  
**Architecture:** Python FastAPI Backend, Jinja2 Server-Side Rendering & REST APIs, PostgreSQL / SQLAlchemy 2.0 ORM, Vanilla HTML5/CSS3/ES6+ JavaScript (Leaflet OSM & Chart.js).

---

## Strategic Overview

Barabanki Connect is designed as a unified digital platform serving citizens, students, businesses, creators, job seekers, and visitors of District Barabanki, UP. It bridges information gaps across local commerce, employment, educational institutes, cultural heritage, and civic announcements.

---

## Phase Breakdown

### Phase 0: Project Inspection & Architecture Planning
- [x] Inspect existing workspace, packages, and environment (`main.py`, Python 3.12, PostgreSQL service availability).
- [x] Define architectural patterns: FastAPI ASGI backend with dual HTML template rendering (Jinja2) and JSON REST API endpoints.
- [x] Address ORM & Authentication architecture: Pure SQLAlchemy 2.0 ORM with PostgreSQL (with automatic SQLite fallback for lightweight local dev/testing), secure bcrypt password hashing, Starlette session cookies + JWT support, role-based access control (Admin, Moderator, Business Owner, Creator, Resident).
- [x] Generate foundational documents: `ROADMAP.md`, `README.md`, `PROJECT_STRUCTURE.md`, `TASKS.md`, `CHANGELOG.md`.

### Phase 1: Project Foundation & Configuration
- [ ] Initialize clean directory structure (`app/core`, `app/models`, `app/schemas`, `app/routers`, `app/static`, `app/templates`, `app/seeds`, `tests`).
- [ ] Create `.gitignore` to protect virtualenvs, cache files, and environment secrets.
- [ ] Create `.env.example` and safe local `.env` configuration.
- [ ] Create `requirements.txt` with exact modern dependencies (FastAPI, Uvicorn, SQLAlchemy, psycopg2-binary, Jinja2, python-multipart, bcrypt, python-jose, pydantic-settings, pytest, httpx).
- [ ] Install missing dependencies in the Python virtual environment and verify runtime imports.
- [ ] Configure database connection factory supporting both PostgreSQL and SQLite fallback.

### Phase 2: Responsive UI Design & Reusable Components
- [ ] Implement responsive CSS design system in `app/static/css/style.css` (custom design tokens, warm civic palette inspired by Uttar Pradesh & Barabanki heritage: saffron/ochre #D97706, royal indigo #1E3A8A, emerald #0D9488, slate neutrals, plus complete dark mode).
- [ ] Build reusable UI components: navigation bar with mobile hamburger drawer, breadcrumbs, status badges, alert banners, cards, statistics tiles, tab bars, modal dialogs, loading skeletons, and empty state widgets.
- [ ] Build core JavaScript modules in `app/static/js/main.js`:
  - Mobile menu toggle and backdrop dismiss
  - Theme switcher (auto/light/dark with `localStorage` persistence)
  - Flash message notifications / toast alerts
  - Reusable Leaflet map initialization helper
  - Reusable Chart.js initialization helper
  - CSRF and API fetch wrapper
  - Client-side form validation

### Phase 3: PostgreSQL Database Models & Authentication
- [ ] Design relational schema with SQLAlchemy 2.0:
  - `User`: Roles (admin, moderator, business_owner, creator, resident), profile, password hash, phone, timestamps.
  - `NewsArticle`: Title, category, content, summary, source attribution, banner image, publication status, view counts.
  - `Event`: Title, dates, location, coordinates (lat/lng), organizer, registration link, category.
  - `Business`: Name, category, address, locality, contact info, coordinates, verification status, rating.
  - `JobListing`: Title, company, job type (full-time, part-time, internship, freelance), salary range, requirements, application link, status.
  - `EducationInstitute`: Category (school, college, coaching, polytechnic), courses, affiliation, address, contact, admissions.
  - `CommunityPost` & `Comment`: Category, content, upvotes, moderation status.
  - `Report`: Moderation flag for posts, comments, businesses, jobs.
  - `ContactMessage`: Civic inquiries and feedback submissions.
  - `CreatorProfile`: Showcase portfolio, craft category, bio, social links.
- [ ] Implement secure authentication:
  - Password hashing via `bcrypt` / `passlib`.
  - Session cookie management with secure flags + JWT Bearer token support.
  - Current user dependency injection with role verification (`require_auth`, `require_role`).
  - Auth routes: Register, Login, Logout, Profile update, Password change.
- [ ] Create database seed script (`app/seeds/seed_data.py`) with authentic Barabanki data (Deva Sharif, Parijaat Tree, Lodheshwar Mahadev, Barabanki Handloom clusters, district degree colleges, transport hubs, verified demonstration data clearly labelled).

### Phase 4: Main Website Pages & Navigation
- [ ] Master Jinja2 layout `base.html` with responsive header, active navigation states, user dropdown, flash alerts, and footer.
- [ ] Home Page (`index.html`): Hero banner, quick service search, statistics counter, latest news marquee, upcoming events preview, featured local businesses, recent job openings, tourism highlights, civic emergency numbers.
- [ ] About Page (`about.html`): District profile, platform mission, civic guides, cultural background.
- [ ] Contact Page (`contact.html`): Direct contact form with validation, emergency helpline directory (Police, Ambulance, Women Helpline, District Administration), location map.
- [ ] Tourism & Heritage Page (`tourism.html`): Interactive Leaflet map with markers for historical and cultural landmarks across Barabanki, photos, historical context, visiting hours.
- [ ] Privacy Policy (`privacy.html`) and Terms of Service (`terms.html`).

### Phase 5: Backend APIs & CRUD Operations
- [ ] Implement REST API routers under `/api/v1/`:
  - `/api/v1/auth`: Authentication and user profile endpoints.
  - `/api/v1/news`: News listing, detail, search, and publishing.
  - `/api/v1/events`: Local events CRUD and calendar feed.
  - `/api/v1/businesses`: Directory CRUD with category and locality filters.
  - `/api/v1/jobs`: Job vacancy listings and submissions.
  - `/api/v1/education`: Directory of colleges, schools, coaching centers.
  - `/api/v1/community`: Posts, comments, and upvotes.
  - `/api/v1/creators`: Local artisans, writers, and developer profiles.
  - `/api/v1/contact`: Inquiries submission.
  - `/api/v1/search`: Global multi-entity search endpoint.
- [ ] Implement corresponding server-rendered web routes under `/` for seamless browser navigation with progressive enhancement.

### Phase 6: Modules Deep Dive
- [ ] **Local News Portal**: Categories (Administration, Development, Culture, Sports, Education), source attribution, reader view with related articles.
- [ ] **Events & Festivals**: Date range filtering, location map integration, organizer details, RSVP / registration modal.
- [ ] **Business Directory**: Filter by locality (Nawabganj, Fatehpur, Ramnagar, Haidergarh, Rudauli, Zaidpur, etc.), category (Textiles/Handloom, Restaurants, Healthcare, Services), map view.
- [ ] **Jobs Board**: Filter by employment type, salary visibility, submission form for local employers with moderation queue.
- [ ] **Education & Skill Hub**: Institutional directory, course offerings, career guidance resources for Barabanki youth.
- [ ] **Community Forum**: Discussion threads, threaded comments, community guidelines enforcement, flagging mechanism.
- [ ] **Local Creators & Artisans**: Handloom weavers, regional storytellers, digital creators portfolio display.
- [ ] **Universal Search**: Real-time debounce search query across all modules.

### Phase 7: Admin Dashboard, Moderation & Security
- [ ] Admin Portal (`/admin`):
  - Metric summary cards (Total users, active listings, pending approvals, unresolved reports).
  - Interactive Chart.js analytics (user growth, module activity distribution).
  - Business verification review workflow.
  - Job vacancy moderation queue.
  - Community moderation panel (resolve or dismiss flagged content).
  - User role management.
- [ ] Security Hardening:
  - CSRF protection on POST forms.
  - Input sanitization and XSS prevention.
  - Rate limiting headers and standard security headers (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options).
  - Strict server-side authorization enforcement.

### Phase 8: Testing, QA & Performance Optimization
- [ ] Comprehensive test suite using `pytest` and `httpx`:
  - Unit tests for password hashing, security utilities, and models.
  - Route tests for public pages (Home, About, News, Events, Businesses, Jobs).
  - Authentication flow tests (Register, Login, Token generation, Protected route access).
  - API CRUD tests for core entities.
  - Admin authorization guard tests.
- [ ] Execute tests and verify zero regressions.
- [ ] Validate responsive layout on various viewport sizes.
- [ ] Verify database seeding and clean startup.

### Phase 9: Deployment Preparation & Documentation
- [ ] Docker containerization (`Dockerfile` and `docker-compose.yml` with PostgreSQL and FastAPI service).
- [ ] Production Uvicorn / Gunicorn configuration (`entrypoint.sh` / service configuration).
- [ ] Finalize `README.md` with complete installation instructions, environment variables guide, and database setup instructions.
- [ ] Update `TASKS.md` and `CHANGELOG.md` with all completed work.

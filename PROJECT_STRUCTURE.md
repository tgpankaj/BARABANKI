# Barabanki Connect — Project Structure

```
Barabanki/
├── .env.example                     # Environment configuration template
├── .env                             # Local environment secrets (ignored by git)
├── .gitignore                       # Git ignore rules for Python, DB, caches
├── CHANGELOG.md                     # Project history and release notes
├── Dockerfile                       # Production container definition
├── docker-compose.yml               # Multi-container orchestration (App + PostgreSQL)
├── main.py                          # Application entry point (ASGI App initialization)
├── PROJECT_STRUCTURE.md             # This structural architecture document
├── README.md                        # Project documentation and quickstart guide
├── requirements.txt                 # Python dependencies
├── ROADMAP.md                       # Comprehensive development roadmap
├── TASKS.md                         # Task checklist with progress tracking
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                        # Core application utilities and configs
│   │   ├── __init__.py
│   │   ├── config.py                # Settings with Pydantic BaseSettings & .env support
│   │   ├── database.py              # SQLAlchemy engine, session maker, base model
│   │   ├── dependencies.py          # FastAPI dependencies (auth, DB session, roles)
│   │   └── security.py              # Password hashing, JWT token handling, CSRF utilities
│   │
│   ├── models/                      # SQLAlchemy 2.0 ORM models
│   │   ├── __init__.py
│   │   ├── business.py              # Business directory and locality records
│   │   ├── community.py             # Community forum posts, comments, upvotes
│   │   ├── contact.py               # Civic inquiries and contact messages
│   │   ├── creator.py               # Local artisans, writers, developer profiles
│   │   ├── education.py             # Schools, colleges, coaching centers
│   │   ├── event.py                 # Local events, cultural festivals
│   │   ├── job.py                   # Local employment vacancies and applications
│   │   ├── news.py                  # Local news articles and source attribution
│   │   ├── report.py                # Content moderation flags
│   │   ├── tourism.py               # Tourist attractions and historical heritage spots
│   │   └── user.py                  # User accounts and role definitions
│   │
│   ├── schemas/                     # Pydantic v2 validation & response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                  # Registration, login, profile schemas
│   │   ├── business.py              # Business create, update, output schemas
│   │   ├── community.py             # Forum post, comment schemas
│   │   ├── education.py             # Education listing schemas
│   │   ├── event.py                 # Event listing and RSVP schemas
│   │   ├── job.py                   # Job post and inquiry schemas
│   │   ├── news.py                  # News article schemas
│   │   └── tourism.py               # Tourist spot schemas
│   │
│   ├── routers/                     # Route controllers (API & Web Pages)
│   │   ├── __init__.py
│   │   ├── admin.py                 # Admin dashboard and moderation routes
│   │   ├── auth.py                  # Login, register, profile web & API routes
│   │   ├── businesses.py            # Business directory web & API routes
│   │   ├── community.py             # Community forum web & API routes
│   │   ├── education.py             # Education portal web & API routes
│   │   ├── events.py                # Events calendar web & API routes
│   │   ├── jobs.py                  # Jobs portal web & API routes
│   │   ├── news.py                  # Local news web & API routes
│   │   ├── tourism.py               # Tourism & places web & API routes
│   │   └── web.py                   # Public pages (Home, About, Contact, Search)
│   │
│   ├── seeds/                       # Database seed and demonstration data
│   │   ├── __init__.py
│   │   └── seed_data.py             # Authentic Barabanki baseline data & demo records
│   │
│   ├── static/                      # Static assets (Vanilla HTML/CSS/JS)
│   │   ├── css/
│   │   │   └── style.css            # Responsive styles, design system, dark mode
│   │   ├── js/
│   │   │   ├── main.js              # Theme switcher, mobile nav, toasts, helpers
│   │   │   ├── map.js               # Leaflet OpenStreetMap interactive integration
│   │   │   └── admin_charts.js      # Chart.js analytics dashboard integration
│   │   └── images/
│   │       └── placeholder.svg      # SVG placeholders for local listings
│   │
│   └── templates/                   # Jinja2 HTML templates
│       ├── base.html                # Master layout with navigation & footer
│       ├── components/              # Reusable template components
│       │   ├── navbar.html          # Responsive navigation bar
│       │   ├── footer.html          # Civic links and information footer
│       │   ├── alerts.html          # Notification banners and flash messages
│       │   └── pagination.html      # Reusable pagination widget
│       ├── pages/                   # Public pages
│       │   ├── index.html           # Comprehensive homepage
│       │   ├── about.html           # District overview and platform mission
│       │   ├── contact.html         # Contact form and emergency civic directory
│       │   ├── search.html          # Unified multi-entity search results
│       │   ├── privacy.html         # Privacy policy
│       │   └── terms.html           # Terms of service
│       ├── auth/                    # Authentication views
│       │   ├── login.html           # User login form
│       │   ├── register.html        # Registration form
│       │   └── profile.html         # User profile and activity view
│       ├── news/                    # News views
│       │   ├── list.html            # News feed with category tabs
│       │   └── detail.html          # Full article reader view
│       ├── events/                  # Events views
│       │   ├── list.html            # Upcoming events list & filter
│       │   └── detail.html          # Event details with map marker
│       ├── businesses/              # Business directory views
│       │   ├── list.html            # Business directory with locality filter
│       │   ├── detail.html          # Business profile & contact details
│       │   └── create.html          # Business submission form
│       ├── jobs/                    # Jobs portal views
│       │   ├── list.html            # Job listings with filter
│       │   ├── detail.html          # Job requirements & application
│       │   └── create.html          # Job posting form
│       ├── education/               # Education portal views
│       │   ├── list.html            # Schools, colleges, coaching directory
│       │   └── detail.html          # Institute courses & admissions
│       ├── community/               # Community forum views
│       │   ├── list.html            # Discussion forum threads
│       │   ├── detail.html          # Thread discussion with comments
│       │   └── create.html          # New post submission
│       ├── tourism/                 # Places and heritage views
│       │   ├── list.html            # Landmark directory with interactive map
│       │   └── detail.html          # Landmark history and visitor info
│       ├── creators/                # Creators showcase
│       │   └── list.html            # Local artisans and creators directory
│       └── admin/                   # Admin portal
│           ├── dashboard.html       # Analytics overview and KPI metrics
│           ├── users.html           # User management table
│           ├── moderation.html      # Flagged content moderation queue
│           └── listings.html        # Approval management for businesses/jobs
│
└── tests/                           # Pytest test suite
    ├── __init__.py
    ├── conftest.py                  # Test database fixtures and HTTP client setup
    ├── test_auth.py                 # Authentication and role permission tests
    ├── test_models.py               # ORM model validation tests
    ├── test_routes.py               # Public web page status code tests
    └── test_api.py                  # API endpoints and CRUD tests
```

# Barabanki Connect — Project Structure

```
Barabanki/
├── .env.example                     # Environment configuration template
├── .env                             # Local environment secrets (ignored by git)
├── .gitignore                       # Git ignore rules for Python, DB, backups, caches
├── alembic.ini                      # Alembic migration configuration
├── CHANGELOG.md                     # Project history and release notes
├── Dockerfile                       # Production container definition
├── docker-compose.yml               # Multi-container orchestration (App + PostgreSQL)
├── init_db.py                       # Unified database initializer and seed runner
├── main.py                          # Application entry point (ASGI App initialization)
├── PROJECT_STRUCTURE.md             # This structural architecture document
├── README.md                        # Project documentation and quickstart guide
├── requirements.txt                 # Python dependencies
├── ROADMAP.md                       # Comprehensive development roadmap
├── TASKS.md                         # Task checklist with progress tracking
│
├── alembic/                         # Database schema migrations
│   ├── env.py                       # Alembic migration environment config
│   ├── script.py.mako               # Migration template
│   └── versions/                    # Versioned schema migration files
│
├── scripts/                         # Operational & maintenance utilities
│   └── db_backup_restore.py         # Hot database backup, verify, and restore script
│
├── app/
│   ├── __init__.py
│   │
│   ├── core/                        # Core application utilities and configs
│   │   ├── __init__.py
│   │   ├── config.py                # Settings with Pydantic BaseSettings & .env support
│   │   ├── database.py              # SQLAlchemy engine, session maker, base model
│   │   ├── dependencies.py          # FastAPI dependencies (auth, DB session, roles)
│   │   ├── rate_limiter.py          # In-memory sliding-window IP/client rate limiter
│   │   └── security.py              # Password hashing, JWT token handling, CSRF utilities
│   │
│   ├── models/                      # SQLAlchemy 2.0 ORM models
│   │   ├── __init__.py
│   │   ├── business.py              # Business directory and locality records
│   │   ├── civic_issue.py           # Civic grievance tracking, upvotes, audit history
│   │   ├── community.py             # Community forum posts, comments, likes
│   │   ├── contact.py               # Civic inquiries and contact messages
│   │   ├── creator.py               # Local artisans, writers, developer profiles
│   │   ├── education.py             # Schools, colleges, coaching centers
│   │   ├── event.py                 # Local events, cultural festivals, RSVPs
│   │   ├── job.py                   # Local employment vacancies and applications
│   │   ├── news.py                  # Local news articles and source attribution
│   │   ├── notification.py          # In-app notifications and user follows
│   │   ├── report.py                # Content moderation flags and audits
│   │   ├── tourism.py               # Tourist attractions and historical heritage spots
│   │   └── user.py                  # User accounts, follow relationships, role definitions
│   │
│   ├── schemas/                     # Pydantic v2 validation & response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                  # Registration, login, profile schemas
│   │   ├── business.py              # Business create, update, output schemas
│   │   ├── civic_issue.py           # Civic issue submission and status schemas
│   │   ├── community.py             # Forum post, comment schemas
│   │   ├── contact.py               # Contact message schema
│   │   ├── education.py             # Education listing schemas
│   │   ├── event.py                 # Event listing and RSVP schemas
│   │   ├── job.py                   # Job post and inquiry schemas
│   │   ├── news.py                  # News article schemas
│   │   ├── notification.py          # Notification and count schemas
│   │   └── tourism.py               # Tourist spot schemas
│   │
│   ├── routers/                     # Route controllers (API & Web Pages)
│   │   ├── __init__.py
│   │   ├── admin.py                 # Admin dashboard, moderation, listing approvals
│   │   ├── auth.py                  # Login, register, profile web & API routes
│   │   ├── businesses.py            # Business directory web & API routes
│   │   ├── civic_issues.py          # Civic issue reporting web & API routes
│   │   ├── community.py             # Community forum web & API routes
│   │   ├── creators.py              # Creators showcase web & API routes
│   │   ├── education.py             # Education portal web & API routes
│   │   ├── events.py                # Events calendar web & API routes
│   │   ├── jobs.py                  # Jobs portal web & API routes
│   │   ├── news.py                  # Local news web & API routes
│   │   ├── notifications.py         # Notification center web & API routes
│   │   ├── tourism.py               # Tourism & places web & API routes
│   │   └── web.py                   # Public pages (Home, About, Contact, Search, Services)
│   │
│   ├── seeds/                       # Database seed and demonstration data
│   │   ├── __init__.py
│   │   └── seed_data.py             # Authentic Barabanki baseline data & demo records
│   │
│   ├── static/                      # Static assets (Vanilla HTML/CSS/JS)
│   │   ├── css/
│   │   │   └── style.css            # Responsive styles, design system tokens
│   │   ├── js/
│   │   │   ├── main.js              # Theme switcher, mobile nav, toasts, helpers
│   │   │   ├── map.js               # Leaflet OpenStreetMap interactive integration
│   │   │   └── admin_charts.js      # Chart.js analytics dashboard integration
│   │   └── images/
│   │       ├── hero-monument.svg    # Deva Sharif / Barabanki monument hero illustration
│   │       ├── logo.svg             # Barabanki Connect vector logo
│   │       └── placeholder.svg      # SVG placeholders for local listings
│   │
│   └── templates/                   # Jinja2 HTML templates
│       ├── base.html                # Master layout with navigation & footer
│       ├── components/              # Reusable template components
│       │   ├── navbar.html          # Responsive navigation bar
│       │   ├── bottom_nav.html      # Mobile sticky bottom navigation bar
│       │   ├── footer.html          # Civic links and information footer
│       │   ├── alerts.html          # Notification banners and flash messages
│       │   └── pagination.html      # Reusable pagination widget
│       ├── errors/                  # Custom error templates
│       │   ├── 404.html             # Not Found error page
│       │   └── 500.html             # Internal Server Error page
│       ├── pages/                   # Public pages
│       │   ├── index.html           # Comprehensive homepage
│       │   ├── about.html           # District overview and platform mission
│       │   ├── contact.html         # Contact form and emergency civic directory
│       │   ├── search.html          # Unified multi-entity search results
│       │   ├── services.html        # Public services & helplines directory
│       │   ├── mobile_preview.html  # Mobile interactive preview showcase
│       │   ├── privacy.html         # Privacy policy
│       │   └── terms.html           # Terms of service
│       ├── auth/                    # Authentication views
│       │   ├── login.html           # User login form
│       │   ├── register.html        # Registration form
│       │   ├── profile.html         # User profile and activity view
│       │   └── public_profile.html  # Public creator / citizen profile
│       ├── issues/                  # Civic issue grievance views
│       │   ├── list.html            # Civic issues listing and status filter
│       │   ├── detail.html          # Issue timeline, upvote, and updates
│       │   └── create.html          # Report new civic issue form
│       ├── notifications/           # Notification views
│       │   └── list.html            # Notifications list and mark read
│       ├── news/                    # News views
│       │   ├── list.html            # News feed with category tabs
│       │   └── detail.html          # Full article reader view
│       ├── events/                  # Events views
│       │   ├── list.html            # Upcoming events list & filter
│       │   ├── detail.html          # Event details with map marker & RSVP
│       │   └── create.html          # Event submission form
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
│       │   ├── list.html            # Discussion forum threads & feed
│       │   ├── detail.html          # Thread discussion with comments & likes
│       │   ├── create.html          # New post submission
│       │   └── edit.html            # Edit existing post form
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
└── tests/                           # Pytest test suite (85 tests, 100% pass)
    ├── __init__.py
    ├── conftest.py                  # Test database fixtures and HTTP client setup
    ├── test_auth.py                 # Authentication and role permission tests
    ├── test_models.py               # ORM model validation tests
    ├── test_routes.py               # Public web page status code tests
    ├── test_api.py                  # API endpoints and CRUD tests
    ├── test_phase2_features.py      # Events, businesses, search, services tests
    ├── test_phase3_features.py      # Posts, likes, profiles, civic issues, notifs
    └── test_phase4_qa_and_security.py # Security headers, CSP, rate limiting, backups
```

# Barabanki Connect (बाराबंकी कनेक्ट)

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.143+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy%202.0-D71F00.svg?style=flat&logo=sqlalchemy)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2018-336791.svg?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Leaflet](https://img.shields.io/badge/Maps-Leaflet%20OSM-199900.svg?style=flat&logo=leaflet)](https://leafletjs.com/)
[![Chart.js](https://img.shields.io/badge/Charts-Chart.js-FF6384.svg?style=flat&logo=chart.js)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, responsive, community-driven civic web platform built specifically for the residents, students, businesses, artisans, job seekers, and visitors of **Barabanki, Uttar Pradesh, India**.

---

## 🌟 Vision & Overview

Barabanki is a culturally vibrant and historically rich district situated adjacent to the state capital Lucknow, renowned for the mystical shrine of **Deva Sharif (Haji Waris Ali Shah)**, the ancient **Lodheshwar Mahadev Temple** at Mahadeva, the celestial **Parijaat Tree** at Kintoor, and its age-old **Handloom and Textile weaving traditions**.

**Barabanki Connect** brings the district into the digital era with:
1. **Local News & Updates**: Verified civic news, developmental announcements, and educational bulletins with full source attribution.
2. **Local Events & Festivals**: Cultural fairs (Deva Mela, Mahadeva Mahotsav), workshops, and community events with calendar views and interactive maps.
3. **Local Business Directory**: Local textile weavers, handicraft artisans, shops, healthcare providers, restaurants, and professional services across tehsils (Nawabganj, Ramnagar, Fatehpur, Haidergarh, Rudauli, Zaidpur).
4. **Jobs & Career Portal**: Opportunities for local youth and graduates from institutions like JNT, Sagar Institute, TRC, and local ITIs.
5. **Education & Skills Hub**: Directory of degree colleges, technical institutes, competitive coaching centers, and admission notices.
6. **Community Forum**: Public civic discussions, issue reporting, neighborhood updates, and citizen feedback with active moderation.
7. **Creators & Artisans Showcase**: Highlighting local master weavers (Zari, Chikan, handloom scarves), writers, poets, and digital creators.
8. **Tourism & Heritage**: Curated visitor guides with OpenStreetMap coordinates, historical context, and visitor guidelines.
9. **Emergency & Civic Helplines**: Quick access to local police, district hospital, fire control, and women helplines.
10. **Interactive Admin Portal**: Real-time KPI statistics via Chart.js, content moderation queues, user management, and verified badge controls.

---

## 🏗️ Architecture & Technology Stack

- **Backend**: Python 3.12 with **FastAPI** (High-performance ASGI framework)
- **Templating**: **Jinja2** for server-rendered, SEO-friendly HTML with fast time-to-first-byte
- **Frontend**: Clean **HTML5, CSS3, Modern ES6+ JavaScript** (No heavy frontend frameworks needed; lightweight, fast on mobile connections)
- **Database & ORM**: **PostgreSQL** with **SQLAlchemy 2.0** ORM (includes auto-fallback to SQLite for easy local dev without external DB setup)
- **Authentication**: Secure **bcrypt** password hashing, HTTP-only session cookies with role-based access control (Admin, Moderator, Business Owner, Creator, Resident), plus JWT bearer tokens for REST APIs
- **Forms & Security**: Pydantic v2 data validation, CSRF tokens, XSS escaping, secure headers
- **Maps**: **Leaflet.js** with OpenStreetMap tiles (no paid API key required)
- **Charts**: **Chart.js** for admin analytics and civic metrics
- **Testing**: **pytest** with test database fixtures and `httpx`

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- PostgreSQL (optional for development; SQLite is used automatically if PostgreSQL credentials are not provided)
- Git

### 2. Setup Virtual Environment & Install Dependencies

```powershell
# Navigate to the project directory
cd C:\Users\hp\OneDrive\Desktop\Projects\Barabanki

# Activate existing virtual environment (or create with python -m venv venv)
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Review `.env` settings. By default, it is configured with a secure development secret key and SQLite fallback. If you wish to use your local PostgreSQL 18 instance:
```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/barabanki_db
```

### 4. Initialize Database & Seed Demonstration Data

Run the database seed utility to create all tables and populate authentic Barabanki baseline data:
```powershell
python -m app.seeds.seed_data
```

This seeds:
- **Admin Account**: `admin@barabanki.local` / `Admin@123456`
- **Moderator Account**: `moderator@barabanki.local` / `Moderator@123456`
- **Resident Account**: `citizen@barabanki.local` / `Citizen@123456`
- Authentic tourist landmarks: Deva Sharif, Parijaat Tree, Lodheshwar Mahadev, Barabanki Clock Tower.
- Authentic educational institutions, handloom clusters, local news, and community discussions.

### 5. Run the Application

```powershell
uvicorn main:app --reload --port 8000
```

Open your browser at:
- **Web App**: http://localhost:8000
- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **ReDoc API Documentation**: http://localhost:8000/redoc
- **Admin Dashboard**: http://localhost:8000/admin (login with `admin@barabanki.local` / `Admin@123456`)

---

## 🧪 Running Automated Tests

```powershell
pytest -v
```

---

## 📁 Project Structure

For a full breakdown of directories and modular design, please refer to [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md).

---

## 🛡️ Security & Privacy Notice

- Demonstration data is clearly labelled.
- Real user passwords are encrypted using multi-round bcrypt.
- CSRF tokens protect all state-modifying POST requests.
- Server-side role guards prevent unauthorized access to administrative functions.

---

## 📄 License
This project is licensed under the MIT License.

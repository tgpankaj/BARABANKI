import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional, get_current_user
from app.core.security import generate_csrf_token, validate_csrf_token
from app.models.job import JobListing
from app.schemas.job import JobListingCreate, JobListingOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/jobs", response_class=HTMLResponse)
def jobs_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(JobListing).filter(JobListing.is_active == True, JobListing.is_approved == True)

    if type:
        query = query.filter(JobListing.job_type == type)

    total_jobs = query.count()
    total_pages = math.ceil(total_jobs / page_size) or 1
    offset = (page - 1) * page_size

    jobs = query.order_by(JobListing.created_at.desc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="jobs/list.html",
        context={
            "active_page": "jobs",
            "current_user": current_user,
            "jobs": jobs,
            "current_page": page,
            "total_pages": total_pages,
            "current_type": type,
        },
    )


@router.get("/jobs/new", response_class=HTMLResponse)
def job_create_view(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
    csrf_token = generate_csrf_token(request.client.host if request.client else "bbk_guest")
    return templates.TemplateResponse(
        request=request,
        name="jobs/create.html",
        context={
            "active_page": "jobs",
            "current_user": current_user,
            "csrf_token": csrf_token,
        },
    )


@router.post("/jobs/new")
def job_create_action(
    request: Request,
    title: str = Form(...),
    company_name: str = Form(...),
    job_type: str = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    description: str = Form(...),
    requirements: str = Form(...),
    salary_range: Optional[str] = Form(None),
    application_email: Optional[str] = Form(None),
    contact_phone: Optional[str] = Form(None),
    csrf_token: str = Form(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session_id = request.client.host if request.client else "bbk_guest"
    if not validate_csrf_token(csrf_token, session_id):
        return RedirectResponse(url="/jobs/new", status_code=303)

    from app.seeds.seed_data import slugify
    base_slug = slugify(f"{title} {company_name}")
    slug = base_slug
    counter = 1
    while db.query(JobListing).filter(JobListing.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    job = JobListing(
        title=title.strip(),
        slug=slug,
        company_name=company_name.strip(),
        job_type=job_type.strip(),
        category=category.strip(),
        location=location.strip(),
        salary_range=salary_range.strip() if salary_range else None,
        description=description.strip(),
        requirements=requirements.strip(),
        application_email=application_email.strip() if application_email else None,
        contact_phone=contact_phone.strip() if contact_phone else None,
        posted_by_id=current_user.id,
        is_approved=True,
        is_active=True,
        is_demo=False,
    )
    db.add(job)
    db.commit()
    return RedirectResponse(url=f"/jobs/{slug}", status_code=303)


@router.get("/jobs/{slug}", response_class=HTMLResponse)
def job_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    job = db.query(JobListing).filter(JobListing.slug == slug, JobListing.is_active == True, JobListing.is_approved == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job vacancy not found.")

    return templates.TemplateResponse(
        request=request,
        name="jobs/detail.html",
        context={
            "active_page": "jobs",
            "current_user": current_user,
            "job": job,
        },
    )


# --- REST API ROUTES ---

@router.get("/api/v1/jobs", response_model=List[JobListingOut])
def api_get_jobs(
    job_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(JobListing).filter(JobListing.is_active == True, JobListing.is_approved == True)
    if job_type:
        query = query.filter(JobListing.job_type == job_type)
    return query.order_by(JobListing.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/api/v1/jobs/{slug}", response_model=JobListingOut)
def api_get_job(
    slug: str,
    db: Session = Depends(get_db),
):
    job = db.query(JobListing).filter(JobListing.slug == slug, JobListing.is_active == True, JobListing.is_approved == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/api/v1/jobs", response_model=JobListingOut, status_code=status.HTTP_201_CREATED)
def api_create_job(
    payload: JobListingCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.seeds.seed_data import slugify
    base_slug = slugify(f"{payload.title} {payload.company_name}")
    slug = base_slug
    counter = 1
    while db.query(JobListing).filter(JobListing.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    job = JobListing(
        title=payload.title,
        slug=slug,
        company_name=payload.company_name,
        job_type=payload.job_type,
        category=payload.category,
        location=payload.location,
        salary_range=payload.salary_range,
        description=payload.description,
        requirements=payload.requirements,
        application_email=payload.application_email,
        application_link=payload.application_link,
        contact_phone=payload.contact_phone,
        is_demo=payload.is_demo,
        posted_by_id=current_user.id,
        is_approved=True,
        is_active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

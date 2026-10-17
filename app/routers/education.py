import math
from typing import Optional, List
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user_optional
from app.models.education import EducationInstitute
from app.schemas.education import EducationInstituteOut

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# --- WEB HTML ROUTES ---

@router.get("/education", response_class=HTMLResponse)
def education_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    page_size = settings.DEFAULT_PAGE_SIZE
    query = db.query(EducationInstitute)

    if category:
        query = query.filter(EducationInstitute.category == category)

    total_insts = query.count()
    total_pages = math.ceil(total_insts / page_size) or 1
    offset = (page - 1) * page_size

    institutes = query.order_by(EducationInstitute.id.asc()).offset(offset).limit(page_size).all()

    return templates.TemplateResponse(
        request=request,
        name="education/list.html",
        context={
            "active_page": "education",
            "current_user": current_user,
            "institutes": institutes,
            "current_page": page,
            "total_pages": total_pages,
            "current_category": category,
        },
    )


@router.get("/education/{slug}", response_class=HTMLResponse)
def education_detail_view(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_optional),
):
    inst = db.query(EducationInstitute).filter(EducationInstitute.slug == slug).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Educational institute not found.")

    return templates.TemplateResponse(
        request=request,
        name="education/detail.html",
        context={
            "active_page": "education",
            "current_user": current_user,
            "institute": inst,
        },
    )


# --- REST API ROUTES ---

@router.get("/api/v1/education", response_model=List[EducationInstituteOut])
def api_get_education(
    category: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(EducationInstitute)
    if category:
        query = query.filter(EducationInstitute.category == category)
    return query.offset(offset).limit(limit).all()


@router.get("/api/v1/education/{slug}", response_model=EducationInstituteOut)
def api_get_institute(
    slug: str,
    db: Session = Depends(get_db),
):
    inst = db.query(EducationInstitute).filter(EducationInstitute.slug == slug).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institute not found.")
    return inst

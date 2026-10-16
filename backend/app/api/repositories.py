from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Interaction, Repository
from app.db.session import get_db
from app.schemas.repository import RepoDetail, RepoOut, RepoPage

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/languages", response_model=list[str])
def list_languages(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Repository.language)
        .where(Repository.language.isnot(None))
        .group_by(Repository.language)
        .order_by(func.count().desc())
        .limit(40)
    ).all()
    return list(rows)


@router.get("", response_model=RepoPage)
def search_repos(
    q: str | None = None,
    language: str | None = None,
    sort: Literal["stars", "forks", "updated"] = "stars",
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Repository)
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Repository.full_name.ilike(like), Repository.description.ilike(like)))
    if language:
        stmt = stmt.where(Repository.language == language)

    order = {
        "stars": Repository.stars.desc(),
        "forks": Repository.forks.desc(),
        "updated": Repository.updated_at.desc().nulls_last(),
    }[sort]

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(order, Repository.repo_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return RepoPage(
        items=[RepoOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{repo_id}", response_model=RepoDetail)
def repo_detail(repo_id: int, db: Session = Depends(get_db)):
    repo = db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(404, "Không tìm thấy repository")

    avg, cnt = db.execute(
        select(func.avg(Interaction.rating), func.count(Interaction.rating)).where(
            Interaction.repo_id == repo_id,
            Interaction.interaction_type == "rate",
        )
    ).one()

    return {
        **RepoOut.model_validate(repo).model_dump(),
        "readme_text": repo.readme_text,
        "avg_rating": round(float(avg), 2) if avg is not None else None,
        "rating_count": cnt,
    }

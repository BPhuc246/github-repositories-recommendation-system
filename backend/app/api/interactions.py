from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.models import Interaction, Repository, User
from app.db.session import get_db
from app.schemas.interaction import FlagIn, RatingIn, RepoState
from app.schemas.repository import RepoOut

router = APIRouter(prefix="/interactions", tags=["interactions"])

OPPOSITE = {"favorite": "dislike", "dislike": "favorite"}


def _ensure_repo(db: Session, repo_id: int) -> None:
    if db.get(Repository, repo_id) is None:
        raise HTTPException(404, "Không tìm thấy repository")


def _clear(db: Session, user_id: int, repo_id: int, itype: str) -> None:
    db.execute(delete(Interaction).where(
        Interaction.user_id == user_id,
        Interaction.repo_id == repo_id,
        Interaction.source == "web_app",
        Interaction.interaction_type == itype,
    ))


def _state(db: Session, user_id: int, repo_id: int) -> RepoState:
    rows = db.execute(
        select(Interaction.interaction_type, Interaction.rating).where(
            Interaction.user_id == user_id,
            Interaction.repo_id == repo_id,
            Interaction.source == "web_app",
        )
    ).all()
    state = {"favorite": False, "disliked": False, "rating": None}
    for itype, rating in rows:
        if itype == "favorite":
            state["favorite"] = True
        elif itype == "dislike":
            state["disliked"] = True
        elif itype == "rate":
            state["rating"] = rating
    return RepoState(**state)


@router.get("/repos/{repo_id}", response_model=RepoState)
def get_state(repo_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _state(db, user.user_id, repo_id)


@router.put("/repos/{repo_id}/favorite", response_model=RepoState)
def set_favorite(repo_id: int, body: FlagIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    _ensure_repo(db, repo_id)
    _clear(db, user.user_id, repo_id, "favorite")
    if body.on:
        _clear(db, user.user_id, repo_id, OPPOSITE["favorite"])
        db.add(Interaction(user_id=user.user_id, repo_id=repo_id,
                           source="web_app", interaction_type="favorite"))
    db.commit()
    return _state(db, user.user_id, repo_id)


@router.put("/repos/{repo_id}/dislike", response_model=RepoState)
def set_dislike(repo_id: int, body: FlagIn, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    _ensure_repo(db, repo_id)
    _clear(db, user.user_id, repo_id, "dislike")
    if body.on:
        _clear(db, user.user_id, repo_id, OPPOSITE["dislike"])
        db.add(Interaction(user_id=user.user_id, repo_id=repo_id,
                           source="web_app", interaction_type="dislike"))
    db.commit()
    return _state(db, user.user_id, repo_id)


@router.put("/repos/{repo_id}/rating", response_model=RepoState)
def set_rating(repo_id: int, body: RatingIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    _ensure_repo(db, repo_id)
    _clear(db, user.user_id, repo_id, "rate")
    if body.rating is not None:
        db.add(Interaction(user_id=user.user_id, repo_id=repo_id, source="web_app",
                           interaction_type="rate", rating=body.rating))
    db.commit()
    return _state(db, user.user_id, repo_id)


@router.get("/favorites", response_model=list[RepoOut])
def list_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = (
        select(Repository)
        .join(Interaction, Interaction.repo_id == Repository.repo_id)
        .where(
            Interaction.user_id == user.user_id,
            Interaction.source == "web_app",
            Interaction.interaction_type == "favorite",
        )
        .order_by(Interaction.created_at.desc())
    )
    return db.scalars(stmt).all()

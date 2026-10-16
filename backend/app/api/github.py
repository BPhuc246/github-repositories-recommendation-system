import datetime as dt
from typing import Literal

import httpx
from cryptography.fernet import InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.models import GithubAccount, Interaction, Repository, User
from app.db.session import get_db
from app.schemas.github import GithubStatus, SyncResult
from app.schemas.repository import RepoOut
from app.services.github_sync import (KIND_TO_TYPE, GithubSyncError, decrypt_token,
                                      sync_github)

router = APIRouter(prefix="/github", tags=["github"])

TYPE_TO_KIND = {v: k for k, v in KIND_TO_TYPE.items()}


@router.get("/status", response_model=GithubStatus)
def github_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acc = db.get(GithubAccount, user.user_id)
    counts = {k: 0 for k in KIND_TO_TYPE}
    if acc is not None:
        rows = db.execute(
            select(Interaction.interaction_type, func.count())
            .where(Interaction.user_id == user.user_id, Interaction.source == "github_import")
            .group_by(Interaction.interaction_type)
        ).all()
        for itype, n in rows:
            if itype in TYPE_TO_KIND:
                counts[TYPE_TO_KIND[itype]] = n
    return GithubStatus(
        linked=acc is not None,
        github_login=user.github_login,
        last_synced_at=acc.last_synced_at if acc else None,
        counts=counts,
    )


@router.post("/sync", response_model=SyncResult)
def sync(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    acc = db.get(GithubAccount, user.user_id)
    if acc is None:
        raise HTTPException(400, "Tài khoản này chưa liên kết GitHub")
    try:
        token = decrypt_token(acc.access_token_enc)
    except InvalidToken:
        raise HTTPException(500, "Không giải mã được token. TOKEN_ENCRYPTION_KEY có thể đã đổi.")

    try:
        counts = sync_github(db, user.user_id, acc.github_id, token)
    except httpx.HTTPStatusError as e:
        db.rollback()
        if e.response.status_code == 401:
            raise HTTPException(401, "Token GitHub đã hết hạn hoặc bị thu hồi. Hãy đăng nhập GitHub lại.")
        raise HTTPException(502, f"GitHub trả lỗi {e.response.status_code} khi đồng bộ")
    except (httpx.HTTPError, GithubSyncError):
        db.rollback()
        raise HTTPException(502, "Không đồng bộ được dữ liệu từ GitHub")

    return SyncResult(synced=counts, synced_at=dt.datetime.now(dt.timezone.utc))


@router.get("/repos", response_model=list[RepoOut])
def github_repos(
    kind: Literal["owner", "collab", "star", "pin"],
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Repository)
        .join(Interaction, Interaction.repo_id == Repository.repo_id)
        .where(
            Interaction.user_id == user.user_id,
            Interaction.source == "github_import",
            Interaction.interaction_type == KIND_TO_TYPE[kind],
        )
        .order_by(Interaction.event_at.desc().nulls_last(), Repository.repo_id)
    )
    return db.scalars(stmt).all()

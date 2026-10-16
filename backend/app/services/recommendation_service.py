from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.models import Interaction, RecommendationLog, Repository

ALGORITHM = "language_popularity_v1"
MODEL_VERSION = "v1"


def recommend(db: Session, user_id: int, limit: int = 10) -> list[Repository]:
    # 1. Ngôn ngữ user thích: từ repo đã yêu thích hoặc đánh giá >= 4 sao
    liked_langs = list(db.scalars(
        select(Repository.language)
        .join(Interaction, Interaction.repo_id == Repository.repo_id)
        .where(
            Interaction.user_id == user_id,
            Repository.language.isnot(None),
            or_(
                Interaction.interaction_type == "favorite",
                and_(Interaction.interaction_type == "rate", Interaction.rating >= 4),
            ),
        )
        .group_by(Repository.language)
        .order_by(func.count().desc())
        .limit(3)
    ))

    # 2. Loại repo user đã tương tác (yêu thích, không thích, đánh giá)
    seen = select(Interaction.repo_id).where(Interaction.user_id == user_id)
    stmt = select(Repository).where(~Repository.repo_id.in_(seen))
    if liked_langs:
        stmt = stmt.where(Repository.language.in_(liked_langs))
    repos = list(db.scalars(stmt.order_by(Repository.stars.desc()).limit(limit)).all())

    # 3. Ghi log để phân tích sau
    top = max((r.stars for r in repos), default=0) or 1
    for rank, repo in enumerate(repos, start=1):
        db.add(RecommendationLog(
            user_id=user_id,
            repo_id=repo.repo_id,
            algorithm=ALGORITHM,
            score=round(repo.stars / top, 6),
            rank_position=rank,
            model_version=MODEL_VERSION,
        ))
    db.commit()
    return repos

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RepoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    repo_id: int
    github_repo_id: int
    full_name: str
    description: str | None
    language: str | None
    topics: list[str] | None
    stars: int
    forks: int
    url: str | None
    created_at: datetime | None
    updated_at: datetime | None


class RepoDetail(RepoOut):
    readme_text: str | None
    avg_rating: float | None
    rating_count: int


class RepoPage(BaseModel):
    items: list[RepoOut]
    total: int
    page: int
    page_size: int

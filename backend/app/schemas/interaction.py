from pydantic import BaseModel, Field


class FlagIn(BaseModel):
    on: bool


class RatingIn(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)


class RepoState(BaseModel):
    favorite: bool
    disliked: bool
    rating: int | None

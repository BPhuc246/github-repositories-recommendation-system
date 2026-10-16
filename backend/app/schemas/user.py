from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str | None = None
    password: str = Field(min_length=6, max_length=72)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str | None
    auth_provider: str
    github_id: int | None
    github_login: str | None
    avatar_url: str | None
    created_at: datetime

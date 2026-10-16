import datetime as dt

from pydantic import BaseModel


class GithubStatus(BaseModel):
    linked: bool
    github_login: str | None
    last_synced_at: dt.datetime | None
    counts: dict[str, int]


class SyncResult(BaseModel):
    synced: dict[str, int]
    synced_at: dt.datetime

import datetime as dt
from collections.abc import Iterator

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import GithubAccount, Interaction, Repository

API = "https://api.github.com"

# Ánh xạ loại quan hệ trong app -> interaction_type trong bảng interactions
KIND_TO_TYPE = {
    "owner": "github_owner",
    "collab": "github_collab",
    "star": "github_star",
    "pin": "github_pin",
}

PINNED_QUERY = """
query {
  viewer {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes { ... on Repository { nameWithOwner } }
    }
  }
}
"""

_fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


class GithubSyncError(Exception):
    pass


def encrypt_token(token: str) -> str:
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(enc: str) -> str:
    return _fernet.decrypt(enc.encode()).decode()


def _parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _paginate(client: httpx.Client, path: str, params: dict | None = None,
              headers: dict | None = None) -> Iterator[dict]:
    page = 1
    while True:
        r = client.get(path, params={**(params or {}), "per_page": 100, "page": page}, headers=headers)
        r.raise_for_status()
        items = r.json()
        yield from items
        if len(items) < 100:
            return
        page += 1


def fetch_github_repos(token: str) -> list[tuple[str, dict, dt.datetime | None]]:
    """Lấy repo từ GitHub: (loại, dữ liệu repo, thời điểm sự kiện)."""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f"Bearer {token}",
    }
    results: list[tuple[str, dict, dt.datetime | None]] = []

    with httpx.Client(base_url=API, headers=headers, timeout=30) as c:
        # Repo bạn sở hữu
        for repo in _paginate(c, "/user/repos", {"affiliation": "owner", "sort": "updated"}):
            results.append(("owner", repo, _parse_dt(repo.get("created_at"))))

        # Repo bạn là cộng tác viên
        for repo in _paginate(c, "/user/repos", {"affiliation": "collaborator", "sort": "updated"}):
            results.append(("collab", repo, None))

        # Repo bạn đã star, kèm thời điểm star
        star_headers = {"Accept": "application/vnd.github.star+json"}
        for item in _paginate(c, "/user/starred", headers=star_headers):
            results.append(("star", item["repo"], _parse_dt(item.get("starred_at"))))

        # Repo ghim: chỉ có qua GraphQL
        gql = c.post("/graphql", json={"query": PINNED_QUERY})
        gql.raise_for_status()
        body = gql.json()
        if body.get("errors"):
            raise GithubSyncError(str(body["errors"]))
        nodes = body["data"]["viewer"]["pinnedItems"]["nodes"]
        for node in nodes:
            name = node.get("nameWithOwner")
            if not name:
                continue  # bỏ qua mục không phải repository
            r = c.get(f"/repos/{name}")
            r.raise_for_status()
            results.append(("pin", r.json(), None))

    return results


def _repo_values(r: dict) -> dict:
    return dict(
        github_repo_id=r["id"],
        full_name=r["full_name"],
        description=r.get("description"),
        language=r.get("language"),
        topics=r.get("topics") or [],
        stars=r.get("stargazers_count", 0),
        forks=r.get("forks_count", 0),
        url=r.get("html_url"),
        created_at=_parse_dt(r.get("created_at")),
        updated_at=_parse_dt(r.get("updated_at")),
    )


def _upsert_repo(db: Session, r: dict) -> int:
    """Thêm repo nếu chưa có, cập nhật nếu đã có (theo github_repo_id). Trả về repo_id."""
    values = _repo_values(r)
    stmt = insert(Repository).values(**values)
    # readme_text không được ghi đè ở đây
    stmt = stmt.on_conflict_do_update(
        index_elements=["github_repo_id"],
        set_={k: stmt.excluded[k] for k in values if k != "github_repo_id"},
    ).returning(Repository.repo_id)
    return db.execute(stmt).scalar_one()


def sync_github(db: Session, user_id: int, github_id: int, token: str) -> dict[str, int]:
    # Nếu việc lấy dữ liệu lỗi, exception được ném ra trước khi có bất kỳ thay đổi nào
    items = fetch_github_repos(token)

    counts = {k: 0 for k in KIND_TO_TYPE}
    seen: list[str] = []

    for kind, repo, event_at in items:
        repo_pk = _upsert_repo(db, repo)
        itype = KIND_TO_TYPE[kind]
        event_id = f"gh:{github_id}:{itype}:{repo['id']}"
        seen.append(event_id)

        db.execute(
            insert(Interaction)
            .values(
                user_id=user_id,
                repo_id=repo_pk,
                source="github_import",
                interaction_type=itype,
                event_id=event_id,
                event_at=event_at,
            )
            .on_conflict_do_update(
                index_elements=["event_id"],
                set_={"event_at": event_at},
            )
        )
        counts[kind] += 1

    # Xóa quan hệ GitHub không còn (ví dụ đã unstar, bỏ ghim, rời khỏi repo)
    db.execute(delete(Interaction).where(
        Interaction.user_id == user_id,
        Interaction.source == "github_import",
        Interaction.event_id.not_in(seen),
    ))

    acc = db.get(GithubAccount, user_id)
    if acc is not None:
        acc.last_synced_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    return counts

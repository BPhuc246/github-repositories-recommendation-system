"""
github_collector.py
-------------------
Thu thập metadata repository công khai từ GitHub Search API.

- Mỗi lần chạy thu thêm tối đa `target` repository MỚI (mặc định 3000).
- Không trùng lặp: loại theo github_repo_id đã có trong data/repositories.csv.
- Lưu checkpoint (data/state.json) để lần chạy sau tiếp tục từ partition kế tiếp,
  nên không quét lại cùng một khoảng truy vấn.
- Xuất:
    data/daily/repositories_YYYYMMDD.csv  -> chỉ dữ liệu của lần chạy hôm nay
    data/repositories.csv                 -> bộ tích lũy, đã loại trùng

Cách dùng:
    export GITHUB_TOKEN=ghp_xxx
    python github_collector.py
    python github_collector.py --target 3000 --no-readme
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

API = "https://api.github.com"
DATA_DIR = Path("data")
DAILY_DIR = DATA_DIR / "daily"
MASTER_CSV = DATA_DIR / "repositories.csv"
STATE_JSON = DATA_DIR / "state.json"

COLUMNS = [
    "github_repo_id", "full_name", "owner_login", "name", "description",
    "language", "topics", "readme_text", "stars", "forks", "watchers",
    "open_issues", "license", "is_fork", "is_archived", "repo_created_at",
    "repo_updated_at", "pushed_at", "html_url", "collected_at",
]

# Các chủ đề truy vấn: ngôn ngữ x khoảng sao x năm tạo.
# Mỗi truy vấn Search API chỉ trả tối đa 1000 kết quả, nên phải chia nhỏ.
LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#",
    "PHP", "Ruby", "C", "Kotlin", "Swift", "Dart", "Scala",
]
STAR_BINS = ["10..49", "50..199", "200..999", "1000..4999", ">=5000"]
YEARS = range(2015, 2027)


# ---------------------------------------------------------------------------
# Truy vấn và phân mảnh
# ---------------------------------------------------------------------------
def build_partitions() -> list[str]:
    """Danh sách truy vấn Search API, mỗi truy vấn là một partition."""
    queries = []
    for year in YEARS:
        for lang in LANGUAGES:
            for stars in STAR_BINS:
                queries.append(
                    f'language:"{lang}" stars:{stars} '
                    f'created:{year}-01-01..{year}-12-31 fork:false'
                )
    return queries


# ---------------------------------------------------------------------------
# HTTP client có xử lý rate limit
# ---------------------------------------------------------------------------
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "repo-dataset-collector/1.0",
    })
    token = os.getenv("GITHUB_TOKEN")
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    else:
        print("CẢNH BÁO: chưa có GITHUB_TOKEN, rate limit rất thấp (10 request/phút cho Search).")
    return s


def _get(session, url, params=None, accept=None, max_retries=5):
    """GET có retry. Trả None nếu 404/422 (không tồn tại hoặc vượt giới hạn 1000 kết quả)."""
    headers = {"Accept": accept} if accept else {}
    for attempt in range(max_retries):
        r = session.get(url, params=params, headers=headers, timeout=30)
        if r.status_code == 200:
            return r
        if r.status_code in (404, 422):
            return None
        if r.status_code in (403, 429):
            if "Retry-After" in r.headers:
                time.sleep(int(r.headers["Retry-After"]) + 1)
                continue
            if r.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(r.headers.get("X-RateLimit-Reset", time.time() + 60))
                time.sleep(max(reset - time.time(), 0) + 2)
                continue
            r.raise_for_status()
        if r.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        r.raise_for_status()
    return None


def search_partition(session, query: str, max_results: int = 1000) -> list[dict]:
    """Lấy tối đa 1000 repository cho một truy vấn (10 trang x 100)."""
    items: list[dict] = []
    for page in range(1, 11):
        r = _get(session, f"{API}/search/repositories", params={
            "q": query, "sort": "stars", "order": "desc",
            "per_page": 100, "page": page,
        })
        if r is None:
            break
        batch = r.json().get("items", [])
        items.extend(batch)
        if len(batch) < 100 or len(items) >= max_results:
            break
        time.sleep(2.1)  # Search API: khoảng 30 request/phút
    return items[:max_results]


def fetch_readme(session, full_name: str, max_chars: int) -> str | None:
    r = _get(session, f"{API}/repos/{full_name}/readme",
             accept="application/vnd.github.raw")
    if r is None:
        return None
    return r.text[:max_chars]


# ---------------------------------------------------------------------------
# Chuyển đổi và lưu trữ
# ---------------------------------------------------------------------------
def to_row(item: dict, collected_at: str) -> dict:
    lic = (item.get("license") or {}).get("spdx_id")
    if lic == "NOASSERTION":
        lic = None
    return {
        "github_repo_id": item["id"],
        "full_name": item["full_name"],
        "owner_login": item["owner"]["login"],
        "name": item["name"],
        "description": item.get("description"),
        "language": item.get("language"),
        "topics": json.dumps(item.get("topics", []), ensure_ascii=False),
        "readme_text": None,
        "stars": item["stargazers_count"],
        "forks": item["forks_count"],
        "watchers": item["watchers_count"],  # Theo API, watchers_count = stargazers_count
        "open_issues": item["open_issues_count"],
        "license": lic,
        "is_fork": item["fork"],
        "is_archived": item["archived"],
        "repo_created_at": item["created_at"],
        "repo_updated_at": item["updated_at"],
        "pushed_at": item.get("pushed_at"),
        "html_url": item["html_url"],
        "collected_at": collected_at,
    }


def load_existing_ids() -> set[int]:
    if not MASTER_CSV.exists():
        return set()
    ids = pd.read_csv(MASTER_CSV, usecols=["github_repo_id"])["github_repo_id"]
    return set(ids.tolist())


def load_state() -> dict:
    if STATE_JSON.exists():
        return json.loads(STATE_JSON.read_text(encoding="utf-8"))
    return {"next_partition": 0}


def collect_new(target: int, with_readme: bool, readme_chars: int):
    session = make_session()
    partitions = build_partitions()
    state = load_state()
    existing = load_existing_ids()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    rows: list[dict] = []
    seen: set[int] = set()
    idx = state["next_partition"] % len(partitions)
    visited = 0

    while len(rows) < target and visited < len(partitions):
        print(f"[partition {idx}] {partitions[idx]} | mới: {len(rows)}/{target}")
        for item in search_partition(session, partitions[idx]):
            rid = item["id"]
            if rid in existing or rid in seen:
                continue
            seen.add(rid)
            row = to_row(item, now)
            if with_readme:
                row["readme_text"] = fetch_readme(session, item["full_name"], readme_chars)
            rows.append(row)
            if len(rows) >= target:
                break
        idx = (idx + 1) % len(partitions)
        visited += 1

    state["next_partition"] = idx
    return rows, state


def save(rows: list[dict], state: dict) -> pd.DataFrame:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().strftime("%Y%m%d")

    daily = pd.DataFrame(rows, columns=COLUMNS)
    daily.to_csv(DAILY_DIR / f"repositories_{today}.csv", index=False, encoding="utf-8-sig")

    if MASTER_CSV.exists():
        old = pd.read_csv(MASTER_CSV)
    else:
        old = pd.DataFrame(columns=COLUMNS)
    master = pd.concat([old, daily], ignore_index=True)
    master = master.drop_duplicates(subset="github_repo_id", keep="first")

    tmp = MASTER_CSV.with_suffix(".tmp")
    master.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, MASTER_CSV)  # ghi nguyên tử, tránh hỏng file nếu lỗi giữa chừng

    STATE_JSON.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return master


# ---------------------------------------------------------------------------
# Kiểm tra chất lượng dữ liệu
# ---------------------------------------------------------------------------
def validate(df: pd.DataFrame):
    html_ok = df["html_url"].fillna("").str.startswith("https://github.com/")
    created = pd.to_datetime(df["repo_created_at"], errors="coerce", utc=True)
    updated = pd.to_datetime(df["repo_updated_at"], errors="coerce", utc=True)
    counts = df[["stars", "forks", "watchers", "open_issues"]]

    checks = {
        "so_dong": len(df),
        "github_repo_id_trung": int(df["github_repo_id"].duplicated().sum()),
        "full_name_khong_khop_owner_name": int(
            (df["full_name"] != df["owner_login"] + "/" + df["name"]).sum()
        ),
        "gia_tri_dem_am": int((counts < 0).any(axis=1).sum()),
        "html_url_sai_dinh_dang": int((~html_ok).sum()),
        "ngay_khong_parse_duoc": int(created.isna().sum() + updated.isna().sum()),
        "created_sau_updated": int((created > updated).sum()),
    }
    missing = df.isna().sum()
    return checks, missing


# ---------------------------------------------------------------------------
# Điều phối
# ---------------------------------------------------------------------------
def run(target: int = 3000, with_readme: bool = True, readme_chars: int = 20000):
    rows, state = collect_new(target, with_readme, readme_chars)
    print(f"Thu thập được {len(rows)} repository mới trong lần chạy này.")
    master = save(rows, state)
    checks, missing = validate(master)
    return master, checks, missing


def main():
    ap = argparse.ArgumentParser(description="Thu thập repository GitHub theo ngày.")
    ap.add_argument("--target", type=int, default=3000, help="Số repo mới cần thu mỗi lần chạy")
    ap.add_argument("--no-readme", action="store_true", help="Không tải README (chạy nhanh hơn)")
    ap.add_argument("--readme-chars", type=int, default=20000, help="Giới hạn số ký tự README")
    args = ap.parse_args()

    master, checks, missing = run(args.target, not args.no_readme, args.readme_chars)
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print(f"Tổng số dòng trong {MASTER_CSV}: {len(master)}")


if __name__ == "__main__":
    main()

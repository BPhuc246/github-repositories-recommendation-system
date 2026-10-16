import datetime as dt
import logging
import secrets
from urllib.parse import urlencode

import bcrypt
import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import GithubAccount, User
from app.db.session import get_db
from app.schemas.user import LoginIn, RegisterIn, UserOut
from app.services.github_sync import encrypt_token

log = logging.getLogger("auth")

router = APIRouter(prefix="/auth", tags=["auth"])
COOKIE = "access_token"
STATE_COOKIE = "oauth_state"
ALGO = "HS256"
GITHUB_SCOPES = "read:user user:email"

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


# ---------- Mật khẩu & JWT ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def check_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode()[:72], hashed.encode())


def create_token(user_id: int) -> str:
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp}, settings.JWT_SECRET, algorithm=ALGO)


def set_auth_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE,
        create_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
        secure=settings.COOKIE_SECURE,
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Chưa đăng nhập")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn")
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(401, "Người dùng không tồn tại")
    return user


def _frontend_error(code: str) -> RedirectResponse:
    """Chuyển lỗi OAuth về trang đăng nhập để hiển thị cho người dùng."""
    return RedirectResponse(f"{settings.FRONTEND_URL}/login?error={code}", status_code=302)


# ---------- Đăng ký / đăng nhập thường ----------
@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.username == body.username)):
        raise HTTPException(409, "Tên đăng nhập đã tồn tại")
    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    set_auth_cookie(response, user.user_id)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username))
    if not user or not user.password_hash or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Sai tên đăng nhập hoặc mật khẩu")
    set_auth_cookie(response, user.user_id)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


# ---------- GitHub OAuth ----------
@router.get("/github/config")
def github_config():
    """Kiểm tra cấu hình OAuth (không trả về secret)."""
    cid = settings.GITHUB_CLIENT_ID
    return {
        "client_id_set": bool(cid),
        "client_secret_set": bool(settings.GITHUB_CLIENT_SECRET),
        "client_id_preview": f"{cid[:4]}..." if cid else None,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "frontend_url": settings.FRONTEND_URL,
    }


@router.get("/github/login")
def github_login():
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        return _frontend_error("github_not_configured")

    state = secrets.token_urlsafe(24)
    query = urlencode({
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": GITHUB_SCOPES,
        "state": state,
        "allow_signup": "true",
    })
    response = RedirectResponse(f"{GITHUB_AUTHORIZE_URL}?{query}", status_code=302)
    response.set_cookie(
        STATE_COOKIE,
        state,
        httponly=True,
        samesite="lax",
        max_age=600,
        path="/",
        secure=settings.COOKIE_SECURE,
    )
    return response


def _upsert_github_user(db: Session, gh: dict) -> User:
    user = db.scalar(select(User).where(User.github_id == gh["id"]))
    if user is None:
        username = gh["login"][:50]
        if db.scalar(select(User).where(User.username == username)):
            # Tránh trùng với tài khoản đăng ký thường
            username = f"{gh['login']}_gh{gh['id']}"[:50]
        user = User(
            username=username,
            auth_provider="github",
            github_id=gh["id"],
            password_hash=None,
        )
        db.add(user)

    user.github_login = gh["login"]
    user.avatar_url = gh.get("avatar_url")
    if not user.email:
        user.email = gh.get("email")
    db.commit()
    db.refresh(user)
    return user


@router.get("/github/callback")
def github_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    # GitHub báo lỗi, ví dụ người dùng bấm Cancel
    if error:
        log.warning("GitHub trả lỗi: %s", error)
        return _frontend_error(f"github_{error}")

    expected = request.cookies.get(STATE_COOKIE)
    if not expected or not state or not secrets.compare_digest(state, expected):
        log.warning("State không khớp (có cookie: %s, có state: %s)", bool(expected), bool(state))
        return _frontend_error("github_state_mismatch")

    if not code:
        return _frontend_error("github_no_code")

    try:
        with httpx.Client(timeout=15) as client:
            tok_res = client.post(
                GITHUB_TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_REDIRECT_URI,
                },
            )
            tok = tok_res.json()
            access_token = tok.get("access_token")
            if not access_token:
                gh_error = tok.get("error", "unknown")
                log.error("Đổi code lấy token thất bại: %s", tok)
                return _frontend_error(f"github_token_{gh_error}")

            gh_res = client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if gh_res.status_code != 200:
                log.error("Gọi /user thất bại: %s %s", gh_res.status_code, gh_res.text)
                return _frontend_error("github_user_failed")
            gh = gh_res.json()
    except httpx.HTTPError:
        log.exception("Lỗi mạng khi gọi GitHub")
        return _frontend_error("github_network_error")

    try:
        user = _upsert_github_user(db, gh)
        account = db.get(GithubAccount, user.user_id)
        if account is None:
            account = GithubAccount(user_id=user.user_id)
            db.add(account)
        account.github_id = gh["id"]
        account.access_token_enc = encrypt_token(access_token)
        account.scopes = GITHUB_SCOPES
        account.last_synced_at = None  # buộc đồng bộ lại khi vào trang GitHub
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Lỗi ghi user/token GitHub vào DB. Kiểm tra đã chạy migration chưa.")
        return _frontend_error("github_db_error")

    log.info("Đăng nhập GitHub thành công: %s (user_id=%s)", user.github_login, user.user_id)
    response = RedirectResponse(f"{settings.FRONTEND_URL}/auth/callback", status_code=302)
    set_auth_cookie(response, user.user_id)
    response.delete_cookie(STATE_COOKIE, path="/")
    return response

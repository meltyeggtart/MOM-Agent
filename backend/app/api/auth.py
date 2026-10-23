"""Accounts and browser sessions.

The session cookie is the only credential. It is HTTP-only so page scripts cannot read
it, and it is stored as a digest so the database alone cannot be used to sign in.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from app.core.settings import settings
from app.db.models import User, UserSession
from app.db.session import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

SESSION_COOKIE = "mom_session"


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class UserRead(BaseModel):
    id: uuid.UUID
    email: str

    @classmethod
    def of(cls, user: User) -> "UserRead":
        return cls(id=user.id, email=user.email)


def _email(value: str) -> str:
    email = value.strip().lower()
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enter a valid email address",
        )
    return email


def _unauthorised() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue"
    )


def _start_session(session: Session, user: User, response: Response) -> None:
    token = new_session_token()
    lifetime = timedelta(days=settings.session_days)
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=datetime.now(UTC) + lifetime,
        )
    )
    session.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(lifetime.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


@router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def register(
    payload: Credentials, session: SessionDep, response: Response
) -> UserRead:
    email = _email(payload.email)
    if session.query(User).filter(User.email == email).one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(email=email, password_hash=hash_password(payload.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    _start_session(session, user, response)
    return UserRead.of(user)


@router.post("/login", response_model=UserRead)
def login(payload: Credentials, session: SessionDep, response: Response) -> UserRead:
    email = _email(payload.email)
    user = session.query(User).filter(User.email == email).one_or_none()
    # One message for both cases, so the response does not reveal which emails exist.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect",
        )

    _start_session(session, user, response)
    return UserRead.of(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, session: SessionDep, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        session.query(UserSession).filter(
            UserSession.token_hash == hash_session_token(token)
        ).delete()
        session.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def current_user(request: Request, session: SessionDep) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorised()

    record = (
        session.query(UserSession)
        .filter(UserSession.token_hash == hash_session_token(token))
        .one_or_none()
    )
    if record is None:
        raise _unauthorised()
    if record.expires_at <= datetime.now(UTC):
        session.delete(record)
        session.commit()
        raise _unauthorised()
    return record.user


CurrentUser = Annotated[User, Depends(current_user)]


@router.get("/me", response_model=UserRead)
def read_me(user: CurrentUser) -> UserRead:
    return UserRead.of(user)

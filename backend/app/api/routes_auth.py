from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import permissions_for_role
from app.models.user import User
from app.schemas.auth import DemoAccountListResponse, LoginRequest, LoginResponse, UserOut
from app.services.audit import write_audit_event
from app.services.auth import DEMO_USERS, authenticate_user, create_access_token, ensure_demo_users, get_current_user


router = APIRouter()


@router.get("/auth/demo-accounts", response_model=DemoAccountListResponse)
def get_demo_accounts(db: Session = Depends(get_db)):
    ensure_demo_users(db)
    usernames = [username for username, _, _ in DEMO_USERS]
    users = (
        db.query(User)
        .filter(User.username.in_(usernames), User.is_active.is_(True))
        .all()
    )
    users_by_username = {user.username: user for user in users}
    return {
        "items": [
            {
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "permissions": permissions_for_role(user.role),
            }
            for username in usernames
            if (user := users_by_username.get(username)) is not None
        ]
    }


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    write_audit_event(
        db,
        user=user,
        action="user_login",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"username": user.username, "role": user.role},
    )

    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": _user_out(user),
    }


@router.get("/auth/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return _user_out(user)


def _user_out(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "permissions": permissions_for_role(user.role),
    }

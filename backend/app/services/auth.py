import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User


ROLES = {"admin", "clinician", "care_coordinator", "data_reviewer"}
DEMO_PASSWORD = "clinsight-demo"
DEMO_USERS = [
    ("admin", "Admin Reviewer", "admin"),
    ("clinician", "Dr. Maya Chen", "clinician"),
    ("care", "Alex Rivera", "care_coordinator"),
    ("reviewer", "Sam Patel", "data_reviewer"),
]

security = HTTPBearer(auto_error=False)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return "pbkdf2_sha256$120000${}${}".format(
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_value, expected_value = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode("ascii"))
        expected = base64.urlsafe_b64decode(expected_value.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def ensure_demo_users(db: Session) -> None:
    for username, full_name, role in DEMO_USERS:
        user = db.query(User).filter(User.username == username).first()
        if user:
            continue
        db.add(
            User(
                username=username,
                full_name=full_name,
                role=role,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
            )
        )
    db.commit()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    ensure_demo_users(db)
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(user: User) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.auth_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": int(expires_at.timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64_json(header)}.{_b64_json(payload)}"
    signature = _b64_bytes(
        hmac.new(settings.auth_secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    )
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        header_value, payload_value, signature = token.split(".", 2)
        signing_input = f"{header_value}.{payload_value}"
        expected_signature = _b64_bytes(
            hmac.new(settings.auth_secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Bad signature")
        payload = json.loads(_b64_decode(payload_value).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("Expired token")
        return payload
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    payload = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or missing")
    return user


def require_roles(*roles: str):
    allowed_roles = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role permissions")
        return user

    return dependency


def log_patient_access(db: Session, user: User, patient_id: int, action: str = "patient_chart_access") -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            username=user.username,
            role=user.role,
            action=action,
            patient_id=patient_id,
        )
    )
    db.commit()


def _b64_json(value: Dict[str, Any]) -> str:
    return _b64_bytes(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64_bytes(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))

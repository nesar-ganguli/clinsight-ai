from typing import List, Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    permissions: List[str]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DemoAccountOut(BaseModel):
    username: str
    full_name: Optional[str]
    role: str
    permissions: List[str]


class DemoAccountListResponse(BaseModel):
    items: List[DemoAccountOut]

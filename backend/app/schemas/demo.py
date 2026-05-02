from typing import List

from pydantic import BaseModel


class DemoUser(BaseModel):
    id: str
    name: str
    role: str
    focus: str
    permissions: List[str]


class DemoUsersResponse(BaseModel):
    users: List[DemoUser]

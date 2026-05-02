from fastapi import APIRouter

from app.schemas.demo import DemoUsersResponse
from app.services.demo_users import list_demo_users

router = APIRouter()


@router.get("/demo-users", response_model=DemoUsersResponse)
def get_demo_users():
    return {"users": list_demo_users()}

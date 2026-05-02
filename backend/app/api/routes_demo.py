from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.demo import DemoUsersResponse
from app.services.auth import require_roles
from app.services.demo_users import list_demo_users

router = APIRouter()


@router.get("/demo-users", response_model=DemoUsersResponse)
def get_demo_users(user: User = Depends(require_roles("admin", "clinician", "care_coordinator", "data_reviewer"))):
    return {"users": list_demo_users()}

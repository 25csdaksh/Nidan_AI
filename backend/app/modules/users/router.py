from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import UserRole, get_current_user_token, require_roles
from app.modules.users.schemas import UserCreate, UserResponse
from app.modules.users.service import UserService

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
async def list_clinicians(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_roles([UserRole.SUPER_ADMIN, UserRole.CHIEF_MEDICAL_OFFICER])),
):
    service = UserService(db)
    return await service.list_users(skip=skip, limit=limit)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_clinician(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _token: dict = Depends(require_roles([UserRole.SUPER_ADMIN])),
):
    service = UserService(db)
    return await service.create_user(payload)


@router.get("/me", response_model=UserResponse)
async def get_current_profile(
    token: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user_id = token.get("sub")
    # If anonymous dev user
    if token.get("is_anonymous"):
        return UserResponse(
            id=user_id,
            email="doctor.review@nidan.ai",
            full_name="Dr. Eleanor Vance (MD)",
            role=UserRole.PHYSICIAN,
            department="Internal Medicine",
            license_number="MED-2024-8891",
            is_active=True,
            created_at=None or "2026-10-04T00:00:00Z",
            updated_at=None or "2026-10-04T00:00:00Z",
        )
    return await service.get_by_id(user_id)

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AppException, ResourceNotFoundError
from app.core.security import get_password_hash
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(f"Clinician/User with ID '{user_id}' not found.")
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_users(self, skip: int = 0, limit: int = 50) -> List[User]:
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_user(self, data: UserCreate) -> User:
        existing = await self.get_by_email(data.email)
        if existing:
            raise AppException("A user with this clinical email already exists.", code="USER_EXISTS", status_code=400)

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=get_password_hash(data.password),
            role=data.role.value,
            license_number=data.license_number,
            department=data.department,
            is_active=data.is_active,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

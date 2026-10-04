from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.modules.auth.schemas import LoginRequest, TokenResponse
from app.modules.users.schemas import UserResponse
from app.modules.users.service import UserService


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_service = UserService(db)

    async def authenticate(self, data: LoginRequest) -> TokenResponse:
        user = await self.user_service.get_by_email(data.email)
        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Invalid clinical credentials provided.")

        if not user.is_active:
            raise UnauthorizedError("Clinical account is deactivated. Contact medical administrator.")

        token = create_access_token(
            subject=user.id,
            role=user.role,
            extra_claims={"email": user.email, "full_name": user.full_name},
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user=UserResponse.model_validate(user),
        )

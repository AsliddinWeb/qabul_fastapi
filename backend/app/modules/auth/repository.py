from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

from app.core.repository import BaseRepository
from app.modules.auth.models import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return await self.get_by(token_hash=token_hash)

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return (await self.session.scalars(stmt)).first()

    async def revoke(self, token: RefreshToken) -> RefreshToken:
        token.revoked_at = datetime.now(timezone.utc)
        await self.session.flush()
        return token

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

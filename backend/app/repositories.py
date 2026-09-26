from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Complaint


class ComplaintRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, complaint: Complaint) -> Complaint:
        self.session.add(complaint)
        await self.session.commit()
        await self.session.refresh(complaint)
        return complaint

    async def get(self, complaint_id):
        return await self.session.get(Complaint, complaint_id)

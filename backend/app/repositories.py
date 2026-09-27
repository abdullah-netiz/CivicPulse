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

    async def update_status(self, complaint: Complaint, new_status: str) -> Complaint:
        complaint.status = new_status
        await self.session.commit()
        await self.session.refresh(complaint)
        return complaint

    async def list_complaints(
        self,
        category: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Complaint], int]:
        from sqlalchemy import select, func

        query = select(Complaint)
        count_query = select(func.count(Complaint.id))

        if category:
            query = query.where(Complaint.category == category)
            count_query = count_query.where(Complaint.category == category)
        if priority:
            query = query.where(Complaint.priority == priority)
            count_query = count_query.where(Complaint.priority == priority)
        if status:
            query = query.where(Complaint.status == status)
            count_query = count_query.where(Complaint.status == status)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(Complaint.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        items_res = await self.session.execute(query)
        items = list(items_res.scalars().all())

        return items, total

    async def get_stats(self) -> dict:
        from sqlalchemy import select, func

        cat_query = select(Complaint.category, func.count(Complaint.id)).group_by(Complaint.category)
        cat_res = await self.session.execute(cat_query)
        by_category = {str(cat): count for cat, count in cat_res.all()}

        prio_query = select(Complaint.priority, func.count(Complaint.id)).group_by(Complaint.priority)
        prio_res = await self.session.execute(prio_query)
        by_priority = {str(prio): count for prio, count in prio_res.all()}

        total_query = select(func.count(Complaint.id))
        total_res = await self.session.execute(total_query)
        total = total_res.scalar() or 0

        return {
            "total": total,
            "by_category": by_category,
            "by_priority": by_priority,
        }

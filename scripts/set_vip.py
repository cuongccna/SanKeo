import sys
import os
import asyncio
from sqlalchemy import select, update

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import AsyncSessionLocal
from src.database.models import User, PlanType
from src.common.config import settings

async def set_vip(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if user:
            user.plan_type = PlanType.VIP
            await session.commit()
            print(f"User {user_id} updated to VIP.")
        else:
            print(f"User {user_id} not found. Creating as VIP...")
            user = User(id=user_id, plan_type=PlanType.VIP)
            session.add(user)
            await session.commit()
            print(f"User {user_id} created as VIP.")

if __name__ == "__main__":
    user_id = settings.ADMIN_ID
    if len(sys.argv) > 1:
        user_id = int(sys.argv[1])
    
    print(f"Setting VIP for user ID: {user_id}")
    asyncio.run(set_vip(user_id))

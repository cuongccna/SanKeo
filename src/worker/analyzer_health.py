"""
Health check utilities for News Analyzer
"""
import asyncio
import json
from datetime import datetime, timezone
from src.common.redis_client import get_redis
from src.common.logger import get_logger
from src.database.db import AsyncSessionLocal
from src.database.models import CryptoNews

logger = get_logger("analyzer_health")


class AnalyzerHealth:
    """Check analyzer service health."""
    
    @staticmethod
    async def check() -> dict:
        """Comprehensive health check."""
        
        health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "unknown",
            "checks": {}
        }
        
        # 1. Redis Queue Check
        try:
            redis = await get_redis()
            queue_size = await redis.llen("queue:raw_messages")
            health["checks"]["redis_queue"] = {
                "status": "healthy",
                "queue_size": queue_size
            }
        except Exception as e:
            health["checks"]["redis_queue"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # 2. Database Check
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func, select
                
                # Count recent records (last 24h)
                result = await session.execute(
                    select(func.count(CryptoNews.id)).where(
                        CryptoNews.created_at >= datetime.now(timezone.utc).replace(day=datetime.now(timezone.utc).day - 1)
                    )
                )
                count_24h = result.scalar() or 0
                
                health["checks"]["database"] = {
                    "status": "healthy",
                    "records_last_24h": count_24h
                }
        except Exception as e:
            health["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # 3. Overall Status
        unhealthy = [
            check for check in health["checks"].values()
            if check.get("status") == "unhealthy"
        ]
        
        if unhealthy:
            health["status"] = "unhealthy"
        else:
            health["status"] = "healthy"
        
        return health
    
    @staticmethod
    async def print_health():
        """Print formatted health check."""
        health = await AnalyzerHealth.check()
        
        print("\n" + "="*60)
        print(f"🏥 ANALYZER HEALTH CHECK")
        print("="*60)
        print(f"Time: {health['timestamp']}")
        print(f"Status: {health['status'].upper()}")
        print("-"*60)
        
        for check_name, check_result in health["checks"].items():
            status_icon = "✅" if check_result.get("status") == "healthy" else "❌"
            print(f"{status_icon} {check_name}:")
            for key, value in check_result.items():
                if key != "status":
                    print(f"   {key}: {value}")
        
        print("="*60 + "\n")
        
        return health


if __name__ == "__main__":
    asyncio.run(AnalyzerHealth.print_health())

"""
NEWS ANALYZER & FILTER PROCESSOR
Xử lý luồng riêng: Redis queue → 3-layer filter → Database

Luồng:
1. Ingestor push messages vào queue:raw_messages (KHÔNG THAY ĐỔI)
2. Analyzer pull từ queue
3. Áp dụng 3-layer filter
4. Lưu vào crypto_news table với dedup
"""
import asyncio
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select, insert, update

from src.common.logger import get_logger
from src.common.redis_client import get_redis
from src.database.db import AsyncSessionLocal
from src.database.models import CryptoNews, NewsDuplicate
from src.worker.filters import MessageFilter, KeywordFilter, ContentAnalyzer

logger = get_logger("analyzer")

QUEUE_RAW_MESSAGES = "queue:raw_messages"
QUEUE_FAILED_MESSAGES = "queue:failed_messages"  # For failed processing


class NewsAnalyzer:
    """Analyze and filter crypto news messages."""
    
    def __init__(self):
        self.processed_count = 0
        self.filtered_count = 0
        self.saved_count = 0
    
    @staticmethod
    def calculate_content_hash(text: str) -> str:
        """Calculate SHA256 hash of normalized text."""
        # Normalize: lowercase, remove extra whitespace
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def process_message(self, message_data: dict) -> Optional[dict]:
        """
        Process single message through 3-layer filter.
        
        Input: {
            "user_id": int,
            "text": str,
            "chat_id": int,
            "message_id": int,
            "source_title": str,
            "message_link": str,
            "image_path": str,
            "tags": list
        }
        
        Returns: Filtered message dict or None if rejected
        """
        try:
            text = message_data.get("text", "")
            chat_id = message_data.get("chat_id", 0)
            message_id = message_data.get("message_id", 0)
            source_title = message_data.get("source_title", "Unknown")
            
            logger.debug(f"Processing message {message_id} from {source_title}")
            
            # Apply 3-layer filter
            should_include, filter_result = await MessageFilter.filter_message(
                text=text,
                source_title=source_title,
                chat_id=chat_id,
                message_id=message_id
            )
            
            if not should_include:
                logger.info(
                    f"❌ Message {message_id} FILTERED OUT - "
                    f"Status: {filter_result.get('layer1_status', 'unknown')}"
                )
                self.filtered_count += 1
                return None
            
            logger.info(f"✅ Message {message_id} PASSED filters - weight={filter_result['ai_score']['final_weight']}")
            
            # Enrich with original data
            result = {
                **message_data,
                **filter_result,
                "content_hash": self.calculate_content_hash(text),
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return None
    
    async def save_to_database(self, filtered_message: dict) -> bool:
        """
        Save filtered message to database.
        Handle deduplication via content_hash.
        """
        try:
            content_hash = filtered_message["content_hash"]
            text = filtered_message.get("text", "")[:500]
            
            async with AsyncSessionLocal() as session:
                # Check if content already exists
                existing = await session.execute(
                    select(CryptoNews).where(CryptoNews.content_hash == content_hash)
                )
                existing_news = existing.scalar_one_or_none()
                
                if existing_news:
                    # Increment occurrence counter
                    existing_news.occurrences += 1
                    existing_news.last_seen_at = datetime.now(timezone.utc)
                    
                    # Save duplicate reference
                    duplicate = NewsDuplicate(
                        content_hash=content_hash,
                        first_news_id=existing_news.id,
                        source_id=filtered_message.get("chat_id", 0),
                        message_id=filtered_message.get("message_id"),
                        cosine_similarity=0.95,
                        text_diff_ratio=0.05
                    )
                    session.add(duplicate)
                    
                    logger.info(
                        f"📝 Updated existing news (id={existing_news.id}), "
                        f"occurrences={existing_news.occurrences}"
                    )
                    
                else:
                    # New news - create record
                    ai_score = filtered_message.get("ai_score", {})
                    content_analysis = filtered_message.get("content_analysis", {})
                    
                    news = CryptoNews(
                        content_hash=content_hash,
                        source_id=filtered_message.get("chat_id", 0),
                        source_name=filtered_message.get("source_title", "Unknown"),
                        message_id=filtered_message.get("message_id"),
                        text_summary=text,
                        # Store full text only if important (weight >= 70)
                        text_full=filtered_message.get("text") if ai_score.get("final_weight", 0) >= 70 else None,
                        
                        # Layer 1 results
                        layer1_matched_keywords=filtered_message.get("keyword_matches"),
                        
                        # Layer 2 results
                        layer2_quality_score=content_analysis.get("quality_score"),
                        layer2_sentiment=content_analysis.get("sentiment", {}).get("sentiment"),
                        layer2_urgency=content_analysis.get("urgency"),
                        layer2_credibility=content_analysis.get("credibility"),
                        
                        # Layer 3 results
                        layer3_relevance=ai_score.get("relevance_score"),
                        layer3_credibility=ai_score.get("credibility_score"),
                        layer3_market_impact=ai_score.get("market_impact"),
                        final_weight=ai_score.get("final_weight"),
                        ai_reasoning=ai_score.get("reasoning"),
                        
                        # Metadata
                        message_link=filtered_message.get("message_link"),
                        image_path=filtered_message.get("image_path"),
                        tags=filtered_message.get("tags", []),
                    )
                    session.add(news)
                    logger.info(
                        f"💾 Saved new news - weight={ai_score.get('final_weight')}, "
                        f"sentiment={content_analysis.get('sentiment', {}).get('sentiment')}"
                    )
                
                await session.commit()
                self.saved_count += 1
                return True
                
        except Exception as e:
            logger.error(f"Error saving to database: {e}", exc_info=True)
            return False
    
    async def process_queue(self, batch_size: int = 10):
        """
        Main loop: process messages from Redis queue.
        """
        redis = await get_redis()
        logger.info(f"🎯 News Analyzer started (batch_size={batch_size})")
        
        while True:
            try:
                # Get batch of messages
                messages = await redis.lrange(QUEUE_RAW_MESSAGES, 0, batch_size - 1)
                
                if not messages:
                    await asyncio.sleep(5)  # Sleep if queue empty
                    continue
                
                logger.debug(f"Processing batch of {len(messages)} messages")
                
                for msg_json in messages:
                    try:
                        message_data = json.loads(msg_json)
                        self.processed_count += 1
                        
                        # Apply filter
                        filtered = await self.process_message(message_data)
                        
                        if filtered:
                            # Save to database
                            await self.save_to_database(filtered)
                        
                        # Remove from queue after processing
                        await redis.lpop(QUEUE_RAW_MESSAGES)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in queue: {e}")
                        await redis.lpop(QUEUE_RAW_MESSAGES)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        # Keep message in queue for retry
                        await asyncio.sleep(1)
                        break
                
                # Log stats
                logger.info(
                    f"📊 Stats - Processed: {self.processed_count}, "
                    f"Filtered: {self.filtered_count}, "
                    f"Saved: {self.saved_count}"
                )
                
            except Exception as e:
                logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(5)


async def main():
    """Start the news analyzer service."""
    analyzer = NewsAnalyzer()
    
    logger.info("=" * 60)
    logger.info("NEWS ANALYZER SERVICE - Starting...")
    logger.info("=" * 60)
    logger.info("Ingestor → queue:raw_messages → Analyzer → 3-Layer Filter → crypto_news")
    logger.info("=" * 60)
    
    try:
        await analyzer.process_queue(batch_size=10)
    except KeyboardInterrupt:
        logger.info("News Analyzer stopped by user.")
    except Exception as e:
        logger.error(f"Analyzer error: {e}")
        raise


if __name__ == "__main__":
    import sys
    import os
    
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    asyncio.run(main())

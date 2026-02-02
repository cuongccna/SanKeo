"""
3-LAYER MESSAGE FILTER SYSTEM
Layer 1: Keyword Matching (Relevance check)
Layer 2: Content Analysis (Quality & sentiment)
Layer 3: Gemini AI Scoring (Final weight decision)
"""
import re
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from src.common.logger import get_logger
from src.common.ai_client import ai_client

logger = get_logger("filter")


# ============ LAYER 1: KEYWORD MATCHING ============
class KeywordFilter:
    """Filter messages by crypto-related keywords."""
    
    # Crypto ticker patterns (simplified for better matching)
    CRYPTO_KEYWORDS = {
        "ticker": r"\$(BTC|ETH|SOL|XRP|ADA|BNB|DOGE|SHIB|LINK|MATIC|FTM|AVAX|NEAR|ARB|OP)|BTC|ETH|SOL|XRP|ADA|BNB",
        "technical": r"\b(bull|bullish|bear|bearish|pump|dump|ath|atl|support|resistance|breakout|consolidation|moon|rocket|dip|hodl)\b",
        "event": r"\b(listing|ido|presale|launch|airdrop|fork|upgrade|merge|burn|mint|stake|unstake|apy|apr)\b",
        "defi": r"\b(defi|swap|yield|farming|liquidity|pool|lptoken|slippage|impermanent|uniswap|aave|curve|lido)\b",
        "social": r"\b(trending|viral|twitter|reddit|discord|telegram|community|influencer|dyor|fud|hopium)\b",
        "exchange": r"\b(binance|coinbase|kraken|bybit|okx|htx|gate|kucoin|dexos|uniswap|pancakeswap)\b",
        "security": r"\b(exploit|hack|rug|scam|rugpull|honeypot|slashing|vulnerable)\b",
        "narrative": r"\b(metaverse|web3|ai|nft|gaming|layer2|zk|rollup|bridge|oracle|dao)\b",
        "onchain": r"\b(whale|onchain|on-chain|glassnode|chainalysis|inflow|outflow|accumulation|distribution)\b"
    }
    
    EXCLUDE_KEYWORDS = {
        "spam": r"\b(follow|subscribe|like|share|retweet|upvote|win|giveaway|contest)\b",
        "pump_dump": r"(pump.*group|signal.*service|guaranteed.*moon|moon.*guaranteed)",
    }
    
    @staticmethod
    def get_matched_categories(text: str) -> Dict[str, List[str]]:
        """
        Match keywords and return matched categories.
        Returns: {"ticker": ["BTC", "ETH"], "technical": ["bull"], ...}
        """
        matched = {}
        text_upper = text.upper()
        
        for category, pattern in KeywordFilter.CRYPTO_KEYWORDS.items():
            matches = re.findall(pattern, text_upper, re.IGNORECASE)
            if matches:
                # Flatten nested tuples from regex groups
                flat_matches = []
                for m in matches:
                    if isinstance(m, tuple):
                        flat_matches.extend([x for x in m if x])
                    else:
                        flat_matches.append(m)
                matched[category] = flat_matches
        
        return matched
    
    @staticmethod
    def is_spam(text: str) -> bool:
        """Check if message is spam."""
        for pattern in KeywordFilter.EXCLUDE_KEYWORDS.values():
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def calculate_relevance_score(matched_categories: Dict) -> float:
        """
        Calculate relevance score (0-100) based on keyword matches.
        More categories matched = higher score.
        """
        if not matched_categories:
            return 0
        
        # Weight categories (higher = more important)
        weights = {
            "ticker": 20,
            "technical": 18,
            "event": 15,
            "defi": 15,
            "social": 10,
            "exchange": 12,
            "security": 18,
            "narrative": 12,
            "onchain": 15
        }
        
        score = 0
        matched_count = 0
        
        for category, matches in matched_categories.items():
            if matches:
                matched_count += 1
                weight = weights.get(category, 10)
                # First match = full weight, additional = half
                if len(matches) == 1:
                    score += weight
                else:
                    score += weight + (len(matches) - 1) * (weight / 2)
        
        # Bonus: multiple categories = higher relevance
        if matched_count >= 2:
            score *= (1 + matched_count * 0.1)  # 10% boost per category
        
        return min(score, 100)


# ============ LAYER 2: CONTENT ANALYSIS ============
class ContentAnalyzer:
    """Analyze message quality and sentiment."""
    
    @staticmethod
    def analyze_sentiment(text: str) -> Dict:
        """
        Analyze message sentiment.
        Returns: {"sentiment": "bullish|neutral|bearish", "confidence": 0-100}
        """
        text_upper = text.upper()
        
        bullish_words = r"\b(moon|rocket|bull|pump|surge|boom|📈|lambo|amazing|gamer|opportunity|bullish)\b"
        bearish_words = r"\b(crash|dump|bear|bearish|fear|bearish|📉|rug|rekt|caution|warning|danger)\b"
        
        bullish_count = len(re.findall(bullish_words, text_upper))
        bearish_count = len(re.findall(bearish_words, text_upper))
        
        if bullish_count > bearish_count:
            return {"sentiment": "bullish", "confidence": min(bullish_count * 20, 100)}
        elif bearish_count > bullish_count:
            return {"sentiment": "bearish", "confidence": min(bearish_count * 20, 100)}
        else:
            return {"sentiment": "neutral", "confidence": 50}
    
    @staticmethod
    def analyze_urgency(text: str) -> str:
        """
        Determine message urgency level.
        Returns: "breaking" | "important" | "regular"
        """
        urgency_patterns = {
            "breaking": r"\b(breaking|urgent|asap|just|now|happening|live|alert|⚠️|🚨)\b",
            "important": r"\b(important|attention|note|fyi|heads.*up|announcement|update)\b",
        }
        
        text_upper = text.upper()
        if re.search(urgency_patterns["breaking"], text_upper, re.IGNORECASE):
            return "breaking"
        elif re.search(urgency_patterns["important"], text_upper, re.IGNORECASE):
            return "important"
        return "regular"
    
    @staticmethod
    def analyze_credibility(source_title: str, message_links: int = 0) -> float:
        """
        Estimate credibility score (0-100) based on source.
        Known crypto sources get higher scores.
        """
        source_upper = source_title.upper()
        
        verified_sources = [
            "bloomberg", "reuters", "cnbc", "ft", "cointelegraph",
            "coindesk", "theblock", "decrypt", "messari", "arkham",
            "chainalysis", "on-chain", "glassnode"
        ]
        
        potential_sources = [
            "crypto", "defi", "nft", "web3", "blockchain", "ethereum",
            "bitcoin", "digital", "token"
        ]
        
        # Check verified sources
        for source in verified_sources:
            if source in source_upper:
                return 90 + (5 if message_links <= 2 else -10)
        
        # Check potential sources
        for source in potential_sources:
            if source in source_upper:
                return 60 + (message_links * 5)
        
        # Unknown sources
        return 30 + (message_links * 5)
    
    @staticmethod
    def calculate_quality_score(text: str, source_title: str) -> Dict:
        """Calculate overall content quality."""
        
        # Check length
        min_length = 30  # minimum meaningful text
        if len(text) < min_length:
            length_score = 20
        elif len(text) > 500:
            length_score = 100
        else:
            length_score = 40 + (len(text) / 500) * 60
        
        # Check for evidence/links
        links = len(re.findall(r"https?://", text))
        link_score = min(links * 15, 100)
        
        # Sentiment confidence
        sentiment = ContentAnalyzer.analyze_sentiment(text)
        sentiment_score = sentiment["confidence"]
        
        # Overall quality
        quality_score = (length_score + link_score + sentiment_score) / 3
        
        return {
            "quality_score": min(quality_score, 100),
            "length_score": length_score,
            "link_count": links,
            "sentiment": sentiment,
            "urgency": ContentAnalyzer.analyze_urgency(text),
            "credibility": ContentAnalyzer.analyze_credibility(source_title, links)
        }


# ============ LAYER 3: GEMINI AI SCORING ============
class AIScorer:
    """Use Gemini AI to score message importance."""
    
    @staticmethod
    async def score_message(
        text: str,
        source_title: str,
        keyword_matches: Dict,
        content_analysis: Dict
    ) -> Dict:
        """
        Use Gemini AI to score final message weight.
        
        Returns: {
            "relevance_score": 0-100,
            "credibility_score": 0-100,
            "impact_score": 0-100,
            "final_weight": 0-100,
            "reasoning": "...",
            "should_include": True|False
        }
        """
        
        try:
            if not ai_client.model:
                logger.warning("AI Client not available, using default scoring")
                return AIScorer._default_scoring(keyword_matches, content_analysis)
            
            prompt = f"""
Analyze this cryptocurrency news message and score it:

SOURCE: {source_title}
TEXT: {text[:500]}

KEYWORD ANALYSIS:
- Matched categories: {json.dumps(keyword_matches, ensure_ascii=False)}
- Quality analysis: {json.dumps(content_analysis, ensure_ascii=False)}

TASK: Provide a JSON response with:
1. relevance_score (0-100): How relevant to crypto news/social?
2. credibility_score (0-100): How trustworthy is this information?
3. market_impact (0-100): Potential impact on crypto markets?
4. final_weight (0-100): Overall importance (0.4*relevance + 0.4*credibility + 0.2*impact)
5. should_include (true/false): Include in news feed?
6. reasoning (string): Brief explanation

Return ONLY valid JSON, no other text.
"""
            
            response = await ai_client.model.generate_content_async(prompt)
            
            # Parse AI response
            try:
                # Extract JSON from response
                json_str = response.text
                if "```" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0]
                
                result = json.loads(json_str)
                
                # Ensure required fields
                result.setdefault("relevance_score", 50)
                result.setdefault("credibility_score", 50)
                result.setdefault("market_impact", 50)
                result.setdefault("final_weight", 50)
                result.setdefault("should_include", True)
                result.setdefault("reasoning", "AI analysis completed")
                
                logger.info(
                    f"AI Score: weight={result['final_weight']}, "
                    f"include={result['should_include']}"
                )
                
                return result
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI response: {e}")
                return AIScorer._default_scoring(keyword_matches, content_analysis)
                
        except Exception as e:
            logger.error(f"AI scoring error: {e}")
            return AIScorer._default_scoring(keyword_matches, content_analysis)
    
    @staticmethod
    def _default_scoring(keyword_matches: Dict, content_analysis: Dict) -> Dict:
        """Fallback scoring when AI is unavailable."""
        # Calculate based on keyword matches and content analysis
        base_score = len(keyword_matches) * 15  # Each category = 15 points
        quality_boost = content_analysis.get("quality_score", 50) * 0.3
        final = min(base_score + quality_boost, 100)
        
        return {
            "relevance_score": min(base_score, 100),
            "credibility_score": content_analysis.get("credibility", 50),
            "market_impact": min(base_score * 0.8, 100),
            "final_weight": final,
            "should_include": final >= 50,
            "reasoning": "Default scoring (AI unavailable)"
        }


# ============ MAIN FILTER ORCHESTRATOR ============
class MessageFilter:
    """Orchestrate all 3 filtering layers."""
    
    MIN_FINAL_WEIGHT = 50  # Threshold to include in feed
    
    @staticmethod
    async def filter_message(
        text: str,
        source_title: str,
        chat_id: int,
        message_id: int
    ) -> Tuple[bool, Dict]:
        """
        Apply all 3 filtering layers.
        
        Returns: (should_include, filter_result_dict)
        """
        
        result = {
            "chat_id": chat_id,
            "message_id": message_id,
            "source": source_title,
            "text_preview": text[:100],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # ===== LAYER 1: Keyword Matching =====
        if KeywordFilter.is_spam(text):
            logger.debug(f"Message {message_id}: REJECTED - SPAM")
            result["layer1_status"] = "rejected_spam"
            return False, result
        
        keyword_matches = KeywordFilter.get_matched_categories(text)
        relevance_score = KeywordFilter.calculate_relevance_score(keyword_matches)
        
        if relevance_score < 15:  # Very low relevance threshold (was 20)
            logger.debug(f"Message {message_id}: REJECTED - LOW RELEVANCE ({relevance_score})")
            result["layer1_status"] = "rejected_low_relevance"
            result["relevance_score"] = relevance_score
            return False, result
        
        result["layer1_status"] = "passed"
        result["relevance_score"] = relevance_score
        result["keyword_matches"] = keyword_matches
        
        # ===== LAYER 2: Content Analysis =====
        content_analysis = ContentAnalyzer.calculate_quality_score(text, source_title)
        
        if content_analysis["quality_score"] < 25:
            logger.debug(f"Message {message_id}: REJECTED - LOW QUALITY")
            result["layer2_status"] = "rejected_low_quality"
            result["content_analysis"] = content_analysis
            return False, result
        
        result["layer2_status"] = "passed"
        result["content_analysis"] = content_analysis
        
        # ===== LAYER 3: Gemini AI Scoring =====
        ai_score = await AIScorer.score_message(
            text, source_title, keyword_matches, content_analysis
        )
        result["layer3_status"] = "scored"
        result["ai_score"] = ai_score
        
        # Final decision
        final_weight = ai_score["final_weight"]
        should_include = ai_score["should_include"] and final_weight >= MessageFilter.MIN_FINAL_WEIGHT
        
        logger.info(
            f"Message {message_id} from {source_title}: "
            f"weight={final_weight}, include={should_include}"
        )
        
        return should_include, result

"""
Test 3-layer filter with sample crypto messages
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set UTF-8 encoding for output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.worker.filters import MessageFilter, KeywordFilter, ContentAnalyzer
from src.common.logger import get_logger

logger = get_logger("test_filter")

# Sample crypto messages
SAMPLE_MESSAGES = [
    {
        "text": "🚨 BREAKING: Bitcoin just broke through $95,000! Technical analysis shows bull flag forming on 4h. BTC dominance surging. #Bitcoin #Bullish 📈",
        "source": "CryptoChanNews",
        "should_pass": True,
        "reason": "High relevance (ticker + technical + breakout)"
    },
    {
        "text": "ETH consolidating at $3,800. Support at $3,700 holding strong. Next resistance at $4,000. Watch for breakout! 🔍",
        "source": "DeFiAnalytics",
        "should_pass": True,
        "reason": "Technical analysis with support/resistance"
    },
    {
        "text": "New listing on Binance! XYZ token launching ASAP. Limited supply presale. Moon potential 🚀 Join our Discord for exclusive info!",
        "source": "UnknownSource",
        "should_pass": False,
        "reason": "Pump & dump scheme, spam keywords"
    },
    {
        "text": "Just made coffee. Coffee is great. Nothing about crypto here.",
        "source": "GeneralChat",
        "should_pass": False,
        "reason": "Zero crypto relevance"
    },
    {
        "text": "SOL on-chain metrics show whale accumulation. Glassnode data indicates institutional inflow. Bearish for shorts 📊",
        "source": "OnchainWizard",
        "should_pass": True,
        "reason": "On-chain metrics + whales + institutional"
    },
    {
        "text": "URGENT: Aave has critical security vulnerability! Exploit detected. $100M at risk. 🚨",
        "source": "BlockSecure",
        "should_pass": True,
        "reason": "Security alert + urgent + high impact"
    },
    {
        "text": "Web3 gaming is the future. Metaverse adoption accelerating. Play-to-earn mechanics revolutionizing gaming. DAOs managing communities.",
        "source": "NarrativeTracker",
        "should_pass": True,
        "reason": "Narrative (web3, gaming, metaverse, dao)"
    },
    {
        "text": "Follow us on Twitter! Like and retweet! Subscribe for updates! Don't miss out!",
        "source": "SpamBot",
        "should_pass": False,
        "reason": "Pure spam"
    },
]


async def test_filter():
    """Test each sample message through 3-layer filter."""
    
    print("=" * 80)
    print("🧪 THREE-LAYER FILTER TEST SUITE")
    print("=" * 80)
    
    results = {
        "passed": 0,
        "failed": 0,
        "correct": 0,
        "incorrect": 0
    }
    
    for idx, sample in enumerate(SAMPLE_MESSAGES, 1):
        print(f"\n{'='*80}")
        print(f"Test {idx}: {sample['source']}")
        print(f"Expected: {'✅ PASS' if sample['should_pass'] else '❌ REJECT'}")
        print(f"Reason: {sample['reason']}")
        print(f"{'-'*80}")
        
        text = sample["text"]
        source = sample["source"]
        
        try:
            # Apply filter
            should_include, filter_result = await MessageFilter.filter_message(
                text=text,
                source_title=source,
                chat_id=12345,
                message_id=idx
            )
            
            # Display Layer 1 results
            print(f"\n📍 LAYER 1: Keyword Matching")
            print(f"   Status: {filter_result.get('layer1_status')}")
            print(f"   Relevance Score: {filter_result.get('relevance_score', 0):.1f}/100")
            if filter_result.get("keyword_matches"):
                print(f"   Matched Keywords: {filter_result['keyword_matches']}")
            
            # Display Layer 2 results
            if filter_result.get("layer2_status") == "passed":
                print(f"\n📍 LAYER 2: Content Analysis")
                content = filter_result.get("content_analysis", {})
                print(f"   Status: {filter_result.get('layer2_status')}")
                print(f"   Quality Score: {content.get('quality_score', 0):.1f}/100")
                print(f"   Sentiment: {content.get('sentiment', {}).get('sentiment')} "
                      f"(confidence: {content.get('sentiment', {}).get('confidence', 0):.0f}%)")
                print(f"   Urgency: {content.get('urgency')}")
                print(f"   Credibility: {content.get('credibility', 0):.0f}/100")
            
            # Display Layer 3 results
            if filter_result.get("layer3_status") == "scored":
                print(f"\n📍 LAYER 3: AI Scoring")
                ai = filter_result.get("ai_score", {})
                print(f"   Relevance: {ai.get('relevance_score', 0):.0f}/100")
                print(f"   Credibility: {ai.get('credibility_score', 0):.0f}/100")
                print(f"   Market Impact: {ai.get('market_impact', 0):.0f}/100")
                print(f"   Final Weight: {ai.get('final_weight', 0):.0f}/100 ⭐")
                print(f"   Reasoning: {ai.get('reasoning')[:100]}")
            
            # Final decision
            print(f"\n{'='*80}")
            if should_include:
                print(f"✅ RESULT: MESSAGE INCLUDED (passed all filters)")
                results["passed"] += 1
            else:
                print(f"❌ RESULT: MESSAGE REJECTED")
                results["failed"] += 1
            
            # Check correctness
            if should_include == sample["should_pass"]:
                print(f"✓ CORRECT: Matched expected result")
                results["correct"] += 1
            else:
                print(f"✗ INCORRECT: Did not match expected result")
                results["incorrect"] += 1
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results["failed"] += 1
    
    # Summary
    print(f"\n\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total tests: {len(SAMPLE_MESSAGES)}")
    print(f"Passed filters: {results['passed']}")
    print(f"Rejected: {results['failed']}")
    print(f"Correct predictions: {results['correct']}/{len(SAMPLE_MESSAGES)}")
    print(f"Accuracy: {(results['correct']/len(SAMPLE_MESSAGES)*100):.1f}%")
    print(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_filter())

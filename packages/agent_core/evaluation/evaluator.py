"""Evaluation utilities for assessing recommendation quality and accuracy."""

from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Optional

from packages.agent_core.models.agent_output import FinalRecommendation
from packages.agent_core.state.agent_state import AgentState
from packages.shared.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AccuracyScore:
    symbol: str
    recommendation: str
    entry_price: float
    exit_price: float
    pct_change: float
    correct: bool
    horizon: str
    analysis_id: Optional[str] = None


@dataclass
class ConsistencyScore:
    symbol: str
    recommendation_counts: dict[str, int] = field(default_factory=dict)
    confidence_mean: float = 0.0
    confidence_std: float = 0.0
    majority_recommendation: Optional[str] = None
    consistency_ratio: float = 0.0


class RecommendationEvaluator:
    """Evaluates the quality and accuracy of agent recommendations."""

    def score_accuracy(
        self,
        recommendation: FinalRecommendation,
        entry_price: float,
        exit_price: float,
    ) -> AccuracyScore:
        """Score a recommendation against actual subsequent price movement.

        Args:
            recommendation: The FinalRecommendation produced by the supervisor agent.
            entry_price:    Price at the time the recommendation was made.
            exit_price:     Price after the time horizon elapsed.

        Returns:
            AccuracyScore with directional correctness and P&L info.
        """
        pct_change = (exit_price - entry_price) / entry_price * 100
        correct = (
            (recommendation.recommendation == "BUY" and pct_change > 2.0)
            or (recommendation.recommendation == "SELL" and pct_change < -2.0)
            or (recommendation.recommendation == "HOLD" and abs(pct_change) <= 5.0)
        )
        return AccuracyScore(
            symbol=recommendation.symbol,
            recommendation=recommendation.recommendation,
            entry_price=entry_price,
            exit_price=exit_price,
            pct_change=round(pct_change, 2),
            correct=correct,
            horizon=recommendation.time_horizon,
            analysis_id=None,
        )

    def measure_agent_consistency(
        self,
        recommendations: list[FinalRecommendation],
    ) -> ConsistencyScore:
        """Measure consistency of recommendations across multiple runs.

        Useful for detecting non-determinism or flip-flopping in the system
        when invoked multiple times under similar market conditions.

        Args:
            recommendations: List of FinalRecommendation objects from repeated runs.

        Returns:
            ConsistencyScore with majority recommendation and consistency ratio.
        """
        if not recommendations:
            return ConsistencyScore(symbol="")

        symbol = recommendations[0].symbol
        counts: dict[str, int] = {"BUY": 0, "HOLD": 0, "SELL": 0}
        confidences = []

        for rec in recommendations:
            counts[rec.recommendation] = counts.get(rec.recommendation, 0) + 1
            confidences.append(rec.confidence)

        majority = max(counts, key=lambda k: counts[k])
        consistency = counts[majority] / len(recommendations)

        return ConsistencyScore(
            symbol=symbol,
            recommendation_counts=counts,
            confidence_mean=round(mean(confidences), 3),
            confidence_std=round(stdev(confidences), 3) if len(confidences) > 1 else 0.0,
            majority_recommendation=majority,
            consistency_ratio=round(consistency, 3),
        )

    def score_agent_agreement(self, state: AgentState) -> dict:
        """Compute the degree of agreement between the three specialized agents.

        Returns a score from 0.0 (no agreement) to 1.0 (full agreement), based
        on whether technical bias, news sentiment, and risk level all point in
        the same direction as the final recommendation.
        """
        final = state.get("final_recommendation")
        technical = state.get("technical_analysis")
        news = state.get("news_analysis")
        risk = state.get("risk_analysis")

        if not final:
            return {"score": 0.0, "agreement_count": 0, "total": 0}

        agreements = 0
        total = 0

        if technical:
            total += 1
            if final.recommendation == "BUY" and technical.overall_technical_bias == "bullish":
                agreements += 1
            elif final.recommendation == "SELL" and technical.overall_technical_bias == "bearish":
                agreements += 1
            elif final.recommendation == "HOLD" and technical.overall_technical_bias == "neutral":
                agreements += 1

        if news:
            total += 1
            if final.recommendation == "BUY" and news.overall_sentiment == "positive":
                agreements += 1
            elif final.recommendation == "SELL" and news.overall_sentiment == "negative":
                agreements += 1
            elif final.recommendation == "HOLD" and news.overall_sentiment == "neutral":
                agreements += 1

        if risk:
            total += 1
            if final.recommendation in ("BUY", "HOLD") and risk.risk_level in ("low", "medium"):
                agreements += 1
            elif final.recommendation == "SELL" and risk.risk_level in ("high", "very_high"):
                agreements += 1

        score = agreements / total if total > 0 else 0.0
        return {
            "score": round(score, 3),
            "agreement_count": agreements,
            "total": total,
            "recommendation": final.recommendation,
        }

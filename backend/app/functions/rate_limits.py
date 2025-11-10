from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..database.models import RateLimitBucket


@dataclass
class RateLimitResult:
    remaining: float
    capacity: int
    reset_at: datetime


class RateLimitExceeded(HTTPException):
    def __init__(self, detail: str = "Rate limit exceeded") -> None:
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


def _refill_tokens(bucket: RateLimitBucket, now: datetime) -> None:
    if bucket.max_tokens <= 0:
        # Unlimited
        bucket.tokens = float(bucket.max_tokens)
        bucket.last_refill = now
        return

    elapsed = (now - bucket.last_refill).total_seconds()
    if elapsed <= 0:
        return

    refill_rate = float(bucket.max_tokens)
    bucket.tokens = min(
        float(bucket.max_tokens),
        bucket.tokens + elapsed * refill_rate,
    )
    bucket.last_refill = now


def consume_rate_limit(
    session: Session,
    *,
    user_id: int,
    limit_type: str,
    cost: float = 1.0,
    error_detail: str | None = None,
) -> RateLimitResult:
    bucket = (
        session.query(RateLimitBucket)
        .filter(
            RateLimitBucket.user_id == user_id,
            RateLimitBucket.limit_type == limit_type,
        )
        .with_for_update()
        .one_or_none()
    )
    if bucket is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rate limit bucket missing")

    now = datetime.utcnow()

    if bucket.max_tokens <= 0:
        # unlimited plan
        bucket.tokens = float(bucket.max_tokens)
        bucket.last_refill = now
        session.add(bucket)
        return RateLimitResult(remaining=float("inf"), capacity=bucket.max_tokens, reset_at=now)

    _refill_tokens(bucket, now)

    if bucket.tokens < cost:
        reset_at = bucket.last_refill + timedelta(seconds=(cost - bucket.tokens) / bucket.max_tokens)
        detail = error_detail or "Rate limit exceeded"
        raise RateLimitExceeded(detail=detail)

    bucket.tokens -= cost
    session.add(bucket)

    reset_at = bucket.last_refill + timedelta(seconds=bucket.tokens / bucket.max_tokens if bucket.max_tokens else 0)
    return RateLimitResult(remaining=bucket.tokens, capacity=bucket.max_tokens, reset_at=reset_at)

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..algorithms.sm2 import SchedulingState, schedule
from ..models import Card, Concept, ReviewLog


def due_cards(session: Session, limit: int = 50) -> list[Card]:
    """Lấy danh sách các thẻ đã đến hạn ôn tập."""
    now = datetime.now(timezone.utc)
    stmt = (
        select(Card)
        .where(Card.due_at <= now)
        .order_by(Card.due_at)
        .limit(limit)
        .options(selectinload(Card.concept).selectinload(Concept.topic))
    )
    return list(session.scalars(stmt))


def review_card(session: Session, card: Card, quality: int, duration_ms: int | None = None) -> Card:
    """Cập nhật thẻ sau khi người dùng trả lời (áp dụng thuật toán SM-2)."""
    # 1. Tính toán lịch mới dựa trên thuật toán SM-2
    result = schedule(
        SchedulingState(card.ease_factor, card.interval, card.repetitions), quality
    )
    
    # 2. Cập nhật thông tin vào thẻ
    card.ease_factor = result.ease_factor
    card.interval = result.interval
    card.repetitions = result.repetitions
    card.due_at = result.due_at
    card.last_reviewed_at = datetime.now(timezone.utc)

    # 3. Lưu lịch sử ôn tập
    session.add(ReviewLog(card_id=card.id, quality=quality, duration_ms=duration_ms))
    return card
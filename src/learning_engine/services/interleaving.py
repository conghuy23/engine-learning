from collections import defaultdict, deque
from typing import Iterable, TypeVar

T = TypeVar("T")


def interleave(items: Iterable[T], topic_of) -> list[T]:
    """Trộn các item (thẻ) sao cho 2 item liên tiếp không cùng chủ đề."""
    buckets: dict[int, deque[T]] = defaultdict(deque)
    for it in items:
        buckets[topic_of(it)].append(it)

    result: list[T] = []
    last_topic: int | None = None

    while any(buckets.values()):
        candidates = [t for t, q in buckets.items() if q and t != last_topic]
        if not candidates:
            candidates = [t for t, q in buckets.items() if q]
        
        # Ưu tiên chọn chủ đề có nhiều thẻ nhất
        topic = max(candidates, key=lambda t: len(buckets[t]))
        result.append(buckets[topic].popleft())
        last_topic = topic

    return result


def build_session(session, limit: int = 20):
    """Lấy thẻ đến hạn và trộn chúng theo chủ đề."""
    from .scheduler import due_cards

    # Lấy gấp 3 lần số lượng để có dư dả mà trộn
    cards = due_cards(session, limit=limit * 3)[: limit * 3]
    cards = interleave(cards, topic_of=lambda c: c.concept.topic_id)
    return cards[:limit]
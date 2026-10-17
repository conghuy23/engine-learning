import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..models import Card, Concept

# Tìm các từ quá dài (dấu hiệu của việc dùng thuật ngữ phức tạp)
_JARGON = re.compile(r"\b\w{14,}\b")


@dataclass
class FeynmanResult:
    explanation: str
    gaps: list[str]


def analyze(explanation: str, *, min_words: int = 40) -> FeynmanResult:
    """Phân tích bài giải thích để tìm lỗ hổng kiến thức."""
    gaps: list[str] = []
    words = explanation.split()

    if len(words) < min_words:
        gaps.append("Bài giải thích quá ngắn, chưa đủ ý.")

    jargon = _JARGON.findall(explanation)
    if jargon:
        gaps.append(f"Có thể đang dùng từ chuyên môn chưa giải thích: {', '.join(sorted(set(jargon)))}")

    if " because " not in explanation.lower() and " vì " not in explanation.lower():
        gaps.append("Thiếu lý do/nguyên nhân (hãy thêm từ 'vì' hoặc 'bởi vì').")

    return FeynmanResult(explanation=explanation, gaps=gaps)


def save_explanation(session: Session, concept: Concept, explanation: str) -> FeynmanResult:
    """Lưu bài giải thích và các lỗ hổng vào database."""
    result = analyze(explanation)
    concept.feynman_explanation = explanation
    concept.gaps = "\n".join(result.gaps) if result.gaps else None
    return result


def gaps_to_cards(session: Session, concept: Concept) -> list[Card]:
    """Biến mỗi lỗ hổng thành một thẻ ghi nhớ (Active Recall)."""
    if not concept.gaps:
        return []
    cards = []
    for gap in concept.gaps.splitlines():
        card = Card(
            concept_id=concept.id,
            front=f"[{concept.title}] Giải thích / khắc phục: {gap}",
            back="(Viết câu trả lời của bạn, sau đó lật thẻ)",
        )
        session.add(card)
        cards.append(card)
    return cards
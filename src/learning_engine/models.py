from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (DateTime, Float, ForeignKey, Integer, String, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class CardType(str, Enum):
    BASIC = "basic"
    CLOZE = "cloze"


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"))
    card_type: Mapped[str] = mapped_column(String(20), default=CardType.BASIC.value)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)

    # SM-2 state
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval: Mapped[int] = mapped_column(Integer, default=0)       # days
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Anki link
    anki_note_id: Mapped[int | None] = mapped_column(Integer)

    concept: Mapped["Concept"] = relationship(back_populates="cards")
    reviews: Mapped[list["ReviewLog"]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str | None] = mapped_column(Text)

    # Feynman artifacts
    feynman_explanation: Mapped[str | None] = mapped_column(Text)
    gaps: Mapped[str | None] = mapped_column(Text)  # newline-separated

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    topic: Mapped["Topic"] = relationship(back_populates="concepts")
    cards: Mapped[list[Card]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    concepts: Mapped[list[Concept]] = relationship(
        back_populates="topic", cascade="all, delete-orphan"
    )


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"))
    quality: Mapped[int] = mapped_column(Integer)          # 0–5
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    card: Mapped[Card] = relationship(back_populates="reviews")
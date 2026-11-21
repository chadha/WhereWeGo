"""SQLAlchemy adapters for collections and behavioral events.

Works with SQLite (local file) and PostgreSQL (docker-compose locally, RDS later).
Tables are created with ``create_all`` for the local demo; Alembic migrations replace this
before any shared environment (ADR-005).

No personal data is stored: session IDs are random, and events are only written with
analytics consent.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Engine,
    Integer,
    String,
    create_engine,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from moment_intelligence.application.collection_store import StoredCollection
from moment_intelligence.domain.contracts import (
    BehavioralEvent,
    Consent,
    MomentCollectionResponse,
)


class Base(DeclarativeBase):
    pass


class CollectionRow(Base):
    __tablename__ = "moment_collections"

    collection_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    consent_analytics: Mapped[bool] = mapped_column(Boolean)
    consent_marketing: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(16), index=True)
    data_source: Mapped[str] = mapped_column(String(32))
    offer_count: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventRow(Base):
    __tablename__ = "behavioral_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    collection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    offer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    schema_version: Mapped[str] = mapped_column(String(8))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)


def make_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return engine


class SqlCollectionStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def put(self, item: StoredCollection) -> None:
        r = item.response
        row = CollectionRow(
            collection_id=r.collection_id,
            request_id=r.request_id,
            session_id=item.session_id,
            consent_analytics=item.consent.analytics,
            consent_marketing=item.consent.marketing,
            status=r.status,
            data_source=r.data_source,
            offer_count=len(r.offers),
            payload=r.model_dump(mode="json"),
            created_at=datetime.now(UTC),
        )
        with Session(self._engine) as session, session.begin():
            session.merge(row)

    def get(self, collection_id: str) -> StoredCollection | None:
        with Session(self._engine) as session:
            row = session.get(CollectionRow, collection_id)
            if row is None:
                return None
            return StoredCollection(
                response=MomentCollectionResponse.model_validate(row.payload),
                session_id=row.session_id,
                consent=Consent(analytics=row.consent_analytics, marketing=row.consent_marketing),
            )

    def status_counts(self) -> dict[str, int]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(CollectionRow.status, func.count()).group_by(CollectionRow.status)
            ).all()
        return {status: int(count) for status, count in rows}

    def offers_shown(self) -> int:
        with Session(self._engine) as session:
            total = session.scalar(select(func.coalesce(func.sum(CollectionRow.offer_count), 0)))
        return int(total or 0)


class SqlEventPublisher:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self.dropped_without_consent = 0

    def publish(self, event: BehavioralEvent) -> bool:
        if not event.consent_state.analytics:
            self.dropped_without_consent += 1
            return False
        row = EventRow(
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            session_id=event.session_id,
            collection_id=event.collection_id,
            offer_id=event.offer_id,
            schema_version=event.schema_version,
            payload=event.model_dump(mode="json"),
        )
        try:
            with Session(self._engine) as session, session.begin():
                session.add(row)
        except IntegrityError:
            return False  # duplicate event_id: idempotent
        return True

    def count_by_type(self) -> dict[str, int]:
        with Session(self._engine) as session:
            rows = session.execute(
                select(EventRow.event_type, func.count()).group_by(EventRow.event_type)
            ).all()
        return {t: int(c) for t, c in rows}

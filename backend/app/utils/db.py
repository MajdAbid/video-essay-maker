from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum as SQLAEnum, JSON, create_engine, select, text
from sqlalchemy import inspect
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlmodel import Field, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import get_settings
from .enums import JobStatus


Base = declarative_base()
settings = get_settings()


class Job(SQLModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "jobs"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    topic: str
    style: str
    length: int = Field(default=60, description="Desired video length in seconds")
    status: JobStatus = Field(
        default=JobStatus.QUEUED,
        sa_column=Column(SQLAEnum(JobStatus, name="job_status")),
    )
    script_status: JobStatus = Field(
        default=JobStatus.QUEUED,
        sa_column=Column(SQLAEnum(JobStatus, name="script_status"), nullable=False),
    )
    audio_status: JobStatus = Field(
        default=JobStatus.NOT_REQUESTED,
        sa_column=Column(SQLAEnum(JobStatus, name="audio_status"), nullable=False),
    )
    video_status: JobStatus = Field(
        default=JobStatus.NOT_REQUESTED,
        sa_column=Column(SQLAEnum(JobStatus, name="video_status"), nullable=False),
    )
    script: Optional[str] = None
    transcript: Optional[str] = None
    image_prompts: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    youtube_context: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )
    review_score: Optional[float] = None
    generation_time: Optional[float] = None
    video_url: Optional[str] = None
    audio_path: Optional[str] = None
    frames_path: Optional[str] = None
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), default=datetime.utcnow),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
        ),
    )
    started_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    finished_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    class Config:
        arbitrary_types_allowed = True


async_engine: AsyncEngine = create_async_engine(
    settings.database_url, future=True, echo=False
)
async_session_factory = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

sync_engine = create_engine(settings.sync_database_url, future=True, echo=False)
sync_session_factory = sessionmaker(sync_engine, expire_on_commit=False)


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(_ensure_transcript_column)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session: AsyncSession = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


@contextmanager
def get_sync_session() -> Session:
    session: Session = sync_session_factory()
    try:
        yield session
    finally:
        session.close()


class JobModel:
    @staticmethod
    async def create(**data: Any) -> Job:
        job = Job(**data)
        async with get_session() as session:
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return job

    @staticmethod
    async def get(job_id: str) -> Optional[Job]:
        async with get_session() as session:
            result = await session.exec(select(Job).where(Job.id == job_id))
            return result.one_or_none()

    @staticmethod
    async def list(limit: int = 20) -> list[Job]:
        async with get_session() as session:
            result = await session.exec(select(Job).order_by(Job.created_at.desc()).limit(limit))
            return result.all()

    @staticmethod
    async def update(job_id: str, **data: Any) -> Job:
        async with get_session() as session:
            result = await session.exec(select(Job).where(Job.id == job_id))
            job = result.one_or_none()
            if not job:
                raise NoResultFound(f"Job {job_id} not found.")

            for key, value in data.items():
                setattr(job, key, value)
            job.updated_at = datetime.utcnow()

            session.add(job)
            await session.commit()
            await session.refresh(job)
        return job

    @staticmethod
    def get_sync(job_id: str) -> Optional[Job]:
        with get_sync_session() as session:
            return session.get(Job, job_id)

    @staticmethod
    def save_sync(job: Job) -> Job:
        job.updated_at = datetime.utcnow()
        with get_sync_session() as session:
            merged = session.merge(job)
            session.commit()
            session.refresh(merged)
        return merged


def get_db() -> AsyncEngine:
    return async_engine


def init_db_sync() -> None:
    SQLModel.metadata.create_all(sync_engine)
    with sync_engine.begin() as conn:
        _ensure_transcript_column(conn)


def _ensure_transcript_column(conn) -> None:
    inspector = inspect(conn)
    if "jobs" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("jobs")}
    if "transcript" not in columns:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN transcript TEXT"))

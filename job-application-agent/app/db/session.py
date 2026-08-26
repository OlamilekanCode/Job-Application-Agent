from collections.abc import Generator

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings


def create_engine_for_settings(settings: Settings | None = None) -> Engine:
    resolved = settings or get_settings()
    connect_args = {}
    if resolved.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(resolved.database_url, connect_args=connect_args, future=True)

    if resolved.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = create_engine_for_settings()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def check_database(session: Session) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    journal_mode = "unknown"
    bind = session.get_bind()
    if bind.dialect.name == "sqlite":
        journal_mode = session.execute(text("PRAGMA journal_mode")).scalar_one()
    return {"status": "healthy", "journal_mode": str(journal_mode)}


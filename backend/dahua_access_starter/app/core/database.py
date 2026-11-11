from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_device_monitoring_columns() -> None:
    """Add monitoring columns to an existing starter SQLite database.

    SQLAlchemy create_all() creates new tables but does not add columns to an
    existing table. This small additive migration preserves existing devices.
    """
    inspector = inspect(engine)
    if "devices" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("devices")}
    dialect = engine.dialect.name
    bool_default = "TRUE" if dialect == "postgresql" else "1"
    datetime_type = "TIMESTAMP WITH TIME ZONE" if dialect == "postgresql" else "DATETIME"
    additions = {
        "monitoring_enabled": f"BOOLEAN NOT NULL DEFAULT {bool_default}",
        "last_health_check_at": f"{datetime_type} NULL",
        "last_tcp_reachable_at": f"{datetime_type} NULL",
        "last_connect_attempt_at": f"{datetime_type} NULL",
        "consecutive_failures": "INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for column_name, definition in additions.items():
            if column_name not in existing:
                connection.execute(
                    text(f"ALTER TABLE devices ADD COLUMN {column_name} {definition}")
                )


def ensure_person_import_columns() -> None:
    """Add provenance fields to existing persons tables without losing records."""
    inspector = inspect(engine)
    if "persons" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("persons")}
    with engine.begin() as connection:
        if "profile_source" not in existing:
            connection.execute(
                text("ALTER TABLE persons ADD COLUMN profile_source VARCHAR(20) NOT NULL DEFAULT 'application'")
            )
        if "source_device_id" not in existing:
            connection.execute(
                text("ALTER TABLE persons ADD COLUMN source_device_id INTEGER NULL")
            )


def ensure_access_card_import_columns() -> None:
    """Add native controller card-state column to existing card assignment tables."""
    inspector = inspect(engine)
    if "access_cards" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("access_cards")}
    if "device_card_status" not in existing:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE access_cards ADD COLUMN device_card_status INTEGER NOT NULL DEFAULT 0")
            )


def ensure_device_identity_columns() -> None:
    """Add hardware identity columns/indexes to existing databases without deleting data."""
    inspector = inspect(engine)
    if "devices" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("devices")}
    with engine.begin() as connection:
        if "serial_number" not in existing_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN serial_number VARCHAR(120) NULL"))
        if "mac_address" not in existing_columns:
            connection.execute(text("ALTER TABLE devices ADD COLUMN mac_address VARCHAR(17) NULL"))

    # Avoid creating duplicate unique indexes when the deployment already has them.
    refreshed = inspect(engine)
    indexes = refreshed.get_indexes("devices")
    unique_columns = {
        tuple(index.get("column_names") or [])
        for index in indexes
        if index.get("unique")
    }
    with engine.begin() as connection:
        if ("serial_number",) not in unique_columns:
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_devices_serial_number ON devices (serial_number)"
            ))
        if ("mac_address",) not in unique_columns:
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_devices_mac_address ON devices (mac_address)"
            ))

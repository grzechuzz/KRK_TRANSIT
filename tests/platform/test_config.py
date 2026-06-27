from sqlalchemy.engine import make_url

from app.platform.config import DatabaseConfig


def test_database_url_preserves_reserved_characters_in_credentials():
    config = DatabaseConfig(
        host="db.internal",
        port=5432,
        name="mpk_db",
        user="mpk:user@example",
        password="p@ss:word/with#chars%25",
    )

    parsed = make_url(config.url_string())

    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.username == "mpk:user@example"
    assert parsed.password == "p@ss:word/with#chars%25"
    assert parsed.host == "db.internal"
    assert parsed.port == 5432
    assert parsed.database == "mpk_db"


def test_database_alembic_url_escapes_percent_for_config_parser():
    config = DatabaseConfig(
        host="db.internal",
        port=5432,
        name="mpk_db",
        user="mpk",
        password="percent%password",
    )

    assert "%25" in config.url_string()
    assert "%%25" in config.alembic_url_string()

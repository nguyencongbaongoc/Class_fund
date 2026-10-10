from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import get_settings

settings = get_settings()

connect_args = {}
if "mysql" in settings.database_url:
    connect_args = {
        "charset": "utf8mb4",
        "autocommit": False,
        "use_unicode": True,
    }
    ssl_dict = {}
    if settings.mysql_ssl_mode:
        ssl_dict["ssl_mode"] = settings.mysql_ssl_mode
    if settings.mysql_ssl_ca:
        ssl_dict["ca"] = settings.mysql_ssl_ca
    if ssl_dict:
        connect_args["ssl"] = ssl_dict
elif "sqlite" in settings.database_url:
    connect_args = {"check_same_thread": False}

engine_kwargs = {
    "future": True,
    "connect_args": connect_args,
}
if "mysql" in settings.database_url:
    engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_timeout": 30,
        "isolation_level": "REPEATABLE_READ",
    })
elif "sqlite" in settings.database_url:
    from sqlalchemy.pool import StaticPool
    engine_kwargs.update({
        "poolclass": StaticPool,
    })

engine = create_engine(
    settings.database_url,
    **engine_kwargs,
)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,
    expire_on_commit=False,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

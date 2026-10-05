from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.dialects.mysql import DATETIME, VARCHAR, JSON as MYSQL_JSON


class Base(DeclarativeBase):
    pass


# MySQL type variants for cross-dialect compatibility
# NOTE: DATETIME's first positional argument is `timezone`, not `fsp`.
# DATETIME(6) silently renders as plain DATETIME (microseconds truncated).
MySQLDateTime = DateTime(timezone=True).with_variant(DATETIME(fsp=6), "mysql")
MySQLString = String
MySQLText = Text
MySQLJSON = JSON().with_variant(MYSQL_JSON(), "mysql")
MySQLVarchar = VARCHAR

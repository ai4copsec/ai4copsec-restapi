from __future__ import annotations
import logging
import sqlalchemy
import json
import re
import numpy as np
from typing import ClassVar, Any, Callable, TypeVar
import datetime as dt
import pydantic

import enum
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    BigInteger,
    Index,
    Integer,
    inspect,
    JSON,
    types,
    String,
    Text,
)

from sqlalchemy.orm import as_declarative, class_mapper
# https://pydoc.dev/sqlalchemy/latest/sqlalchemy.dialects.postgresql.ARRAY.html
# https://docs.sqlalchemy.org/en/14/dialects/postgresql.html#sqlalchemy.dialects.postgresql.hstore
from sqlalchemy.dialects.postgresql import (
    HSTORE,
    ARRAY
)
from sqlalchemy.sql.functions import GenericFunction
from sqlalchemy.ext.compiler import compiles

import ai4copsec.restapi.timescaledb as timescaledb # noqa

__all__ = [ "timescaledb" ]


logger = logging.getLogger(__name__)

T = TypeVar("T")
Xint = BigInteger
DateTimeTZAware = DateTime(timezone=True)

ExtraIndexPrefix : str = "ix_"


# Ensure consistent time handling
class EpochFn(GenericFunction):
    type = DateTime()
    inherit_cache = True

# For PostgreSQL, we will use the `EXTRACT(EPOCH FROM <datetime>)` syntax
@compiles(EpochFn, 'postgresql')
def compile_epoch_fn_postgresql(expr, compiler, **kwargs):
    return f"EXTRACT(EPOCH FROM {compiler.process(expr.clauses.clauses[0], **kwargs)})"

# For TimeScaledb
@compiles(EpochFn, 'timescaledb')
def compile_epoch_fn_timescaledb(expr, compiler, **kwargs):
    return f"EXTRACT(EPOCH FROM {compiler.process(expr.clauses.clauses[0], **kwargs)})"

# For SQLite, we use `strftime('%s', datetime_column)` to get epoch
@compiles(EpochFn, 'sqlite')
def compile_epoch_fn_sqlite(expr, compiler, **kwargs):
    return f"strftime('%s', {compiler.process(expr.clauses.clauses[0], **kwargs)})"

def Column(*args, **kwargs):
    if "nullable" not in kwargs:
        kwargs.setdefault("nullable", False)

    column_type = args[0]
    if 'default' not in kwargs:
        if column_type in [Integer, BigInteger, Float]:
            kwargs.setdefault('default', 0)
        elif column_type in [Text, String]:
            kwargs.setdefault('default', '')

    comment = {}
    if "desc" in kwargs:
        comment["desc"] = kwargs['desc'].strip()
        del kwargs['desc']

    if "unit" in kwargs:
        comment["unit"] = kwargs['unit'].strip()
        del kwargs['unit']

    if comment:
        kwargs["comment"] = json.dumps(comment)

    return sqlalchemy.Column(*args, **kwargs)


def ensure_non_negative(*column_names) -> list[CheckConstraint]:
    return [
       CheckConstraint(f"{x} >= 0", name=f"{x}_is_not_negative") for x in column_names
    ]


class HStoreModel(types.TypeDecorator):
    impl = HSTORE

    required: ClassVar[list[str]] = []
    optional: ClassVar[list[str]] = []

    @property
    def allowed(self):
        return self.required + self.optional

    def process_bind_param(self, value, dialect):
        if value is None or type(value) is not dict:
            raise KeyError(f"{self.__class__}: value must be dictionary")

        for key in self.required:
            if key not in value:
                raise KeyError(f"{self.__class__}: value misses the required key '{key}'")

        for key in value:
            if key not in self.allowed:
                raise KeyError(f"{self.__class__}: value contains an invalid key '{key}'."
                    " Permitted are {','.join(allowed)}")
        return value

    def process_result_value(self, value, dialect):
        return value


@as_declarative()
class TableBase:
    __table__: ClassVar[Any]
    __tablename__: ClassVar[str]
    metadata: ClassVar[Any]

    __extra_values__: ClassVar[pydantic.config.ExtraValues] =  'allow'

    _primary_key_columns: ClassVar[list[str]] = None
    _non_primary_key_columns: ClassVar[list[str]] = None

    def __iter__(self):
        return (
            (c.key, getattr(self, c.key)) for c in inspect(self).mapper.column_attrs
        )

    def _asdict(self):
        return dict(self)

    def __eq__(self, other):
        return type(self) is type(other) and tuple(self) is tuple(other)

    @classmethod
    def create(cls, **kwargs):
        if cls.__extra_values__ == 'forbid':
            return cls(**kwargs)
        else:
            return cls(**cls.known_columns(**kwargs))

    @classmethod
    def unknown_columns(cls, **kwargs):
        """
        Filter out all unknown arguments that cannot be mapped to columns
        """
        return {x:y for x,y in kwargs.items() if x not in cls.__table__.columns}

    @classmethod
    def known_columns(cls, **kwargs) -> dict[str, Column]:
        """
        Filter out all arguments that cannot be mapped to columns
        """
        return {x:y for x,y in kwargs.items() if x in cls.__table__.columns}

    @classmethod
    def primary_key_columns(cls):
        if not cls._primary_key_columns:
            cls._primary_key_columns = [x.name for x in cls.__table__.columns if x.primary_key]
        return cls._primary_key_columns

    @classmethod
    def non_primary_key_columns(cls):
        if not cls._non_primary_key_columns:
            cls._non_primary_key_columns = [x.name for x in cls.__table__.columns if not x.primary_key]
        return cls._non_primary_key_columns

    def get_timeseries_id(self) -> str:
        """
        Get the id for the timeseries - so excluding the timestamp field
        """
        return '.'.join([str(getattr(self, x)) for x in self.primary_key_columns() if x != "time"])

    @classmethod
    def merge(cls,
            samples: list[T],
            merge_op: Callable[list[int | float]] | None = np.mean) -> T:
        values = {}

        reference_sample = samples[-1]
        reference_sample_timeseries_id = reference_sample.get_timeseries_id()
        for sample in samples:
            timeseries_id = sample.get_timeseries_id()
            assert timeseries_id == reference_sample_timeseries_id, \
                    f"sample id {timeseries_id} does not match reference_sample {reference_sample_timeseries_id}"

            for attribute in cls.non_primary_key_columns():
                value = getattr(sample, attribute)
                if attribute not in values:
                    values[attribute] = [value]
                else:
                    values[attribute].append(value)
        kwargs = {}

        static_columns = ["time"]
        static_columns.extend(cls.primary_key_columns())

        for column_name in static_columns:
            kwargs[column_name] = getattr(reference_sample, column_name)

            for column_name in cls.non_primary_key_columns():
                try:
                    kwargs[column_name] = merge_op(values[column_name])
                except TypeError as e:
                    column = getattr(cls, column_name)
                    if column.nullable or column.type.python_type is str:
                        kwargs[column_name] = getattr(reference_sample, column_name)
                    else:
                        raise RuntimeError(f"Merging failed for column: '{column_name}'") from e

        return cls(**kwargs)

class ErrorMessage(TableBase):
    __tablename__ = "error_message"
    __table_args__ = (
        {
            'info': { 'sonar_spec': 'ErrorObject' },
            'timescaledb_hypertable': {
                'time_column_name': 'time',
                'chunk_time_interval': '24 hours',
                'compression': {
                    'segmentby': 'cluster, node',
                    'orderby': 'time',
                    'interval': '7 days'
                }
            }
        }
    )
    cluster = Column(String, primary_key=True, index=True)
    node = Column(String, primary_key=True, index=True)
    detail = Column(Text)

    time = Column(DateTimeTZAware, default=dt.datetime.now, primary_key=True)


class UserSettings(TableBase):
    __tablename__ = "user_settings"

    user = Column(String, primary_key=True, index=True)
    settings = Column(JSON)

    time_modified = Column(DateTimeTZAware, default=dt.datetime.now)

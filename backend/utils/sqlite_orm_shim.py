"""
Minimal drop-in ORM shim providing the small subset of the
Flask-SQLAlchemy / SQLAlchemy API used by this project:

    db.Model, db.Column, db.Integer, db.String, db.Text, db.Float,
    db.Boolean, db.DateTime, db.session.add/commit/delete/rollback,
    Model.query.filter_by(...).first()/.all()/.order_by()/.count()/.get()

This shim exists ONLY so the project remains runnable in environments
where `pip install -r requirements.txt` has not been run yet (e.g. an
offline sandbox). When flask_sqlalchemy is installed, extensions.py
uses the real library instead and this file is not imported.

It is intentionally small: it supports exactly what this project's
models need, not the full SQLAlchemy API.
"""
import sqlite3
import threading
from datetime import datetime


class Column:
    def __init__(self, col_type, primary_key=False, nullable=True,
                 unique=False, default=None, index=False):
        self.type = col_type
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.default = default
        self.index = index
        self.name = None  # set by metaclass


class Integer:
    sql_type = "INTEGER"


class String:
    sql_type = "TEXT"

    def __init__(self, length=None):
        self.length = length


class Text:
    sql_type = "TEXT"


class Float:
    sql_type = "REAL"


class Boolean:
    sql_type = "INTEGER"


class DateTime:
    sql_type = "TEXT"


def _py_to_sql(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return int(value)
    return value


def _sql_to_py(value, col_type):
    if value is None:
        return None
    if isinstance(col_type, DateTime):
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return value
    if isinstance(col_type, Boolean):
        return bool(value)
    return value


class _QueryResultDescOrAsc:
    """Wraps a column reference for order_by(Model.field.desc())."""

    def __init__(self, name, direction="ASC"):
        self.name = name
        self.direction = direction


class _InstrumentedAttribute:
    def __init__(self, name):
        self.name = name

    def desc(self):
        return _QueryResultDescOrAsc(self.name, "DESC")

    def asc(self):
        return _QueryResultDescOrAsc(self.name, "ASC")


class Query:
    def __init__(self, model):
        self.model = model
        self._filters = {}
        self._order = None
        self._limit = None

    def filter_by(self, **kwargs):
        self._filters.update(kwargs)
        return self

    def order_by(self, order_col):
        self._order = order_col
        return self

    def limit(self, n):
        self._limit = n
        return self

    def _build_sql(self, select="*"):
        table = self.model.__tablename__
        sql = f"SELECT {select} FROM {table}"
        params = []
        if self._filters:
            clauses = []
            for k, v in self._filters.items():
                clauses.append(f"{k} = ?")
                params.append(_py_to_sql(v))
            sql += " WHERE " + " AND ".join(clauses)
        if self._order is not None:
            sql += f" ORDER BY {self._order.name} {self._order.direction}"
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        return sql, params

    def all(self):
        conn = self.model._get_conn()
        sql, params = self._build_sql()
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return [self.model._row_to_obj(r) for r in rows]

    def first(self):
        self._limit = 1
        results = self.all()
        return results[0] if results else None

    def get(self, id_):
        return self.model.query.filter_by(id=id_).first()

    def count(self):
        conn = self.model._get_conn()
        sql, params = self._build_sql(select="COUNT(*) as cnt")
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return row["cnt"] if row else 0


class _ModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        columns = {}
        for base in bases:
            if hasattr(base, "_columns"):
                columns.update(base._columns)
        for key, value in list(namespace.items()):
            if isinstance(value, Column):
                value.name = key
                columns[key] = value
        namespace["_columns"] = columns
        cls = super().__new__(mcs, name, bases, namespace)
        for key, col in columns.items():
            setattr(cls, key, _InstrumentedAttribute(key))
        return cls


class Model(metaclass=_ModelMeta):
    _db = None  # injected by SQLAlchemy() instance

    def __init__(self, **kwargs):
        for name, col in self._columns.items():
            setattr(self, name, kwargs.get(name, col.default))
        self._is_new = True

    @classmethod
    def _get_conn(cls):
        return cls._db.connection

    @classmethod
    def _row_to_obj(cls, row):
        obj = cls.__new__(cls)
        for name, col in cls._columns.items():
            setattr(obj, name, _sql_to_py(row[name], col.type))
        obj._is_new = False
        return obj

    @property
    def query(self):  # pragma: no cover - instances use classmethod version
        return Query(self.__class__)

    def to_insert_dict(self):
        d = {}
        for name, col in self._columns.items():
            if name == "id" and getattr(self, "id", None) is None:
                continue
            d[name] = _py_to_sql(getattr(self, name, col.default))
        return d


class _classproperty:
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, owner):
        return self.fget(owner)


Model.query = _classproperty(lambda cls: Query(cls))


class _Session:
    def __init__(self, db):
        self.db = db
        self._pending_new = []
        self._pending_dirty = []
        self._pending_delete = []

    def add(self, instance):
        if getattr(instance, "_is_new", True):
            self._pending_new.append(instance)
        else:
            self._pending_dirty.append(instance)

    def delete(self, instance):
        self._pending_delete.append(instance)

    def commit(self):
        conn = self.db.connection
        try:
            for instance in self._pending_new:
                table = instance.__tablename__
                data = instance.to_insert_dict()
                cols = ", ".join(data.keys())
                placeholders = ", ".join(["?"] * len(data))
                cur = conn.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                    list(data.values()),
                )
                instance.id = cur.lastrowid
                instance._is_new = False

            for instance in self._pending_dirty:
                table = instance.__tablename__
                data = instance.to_insert_dict()
                set_clause = ", ".join(f"{k} = ?" for k in data.keys())
                conn.execute(
                    f"UPDATE {table} SET {set_clause} WHERE id = ?",
                    list(data.values()) + [instance.id],
                )

            for instance in self._pending_delete:
                table = instance.__tablename__
                conn.execute(f"DELETE FROM {table} WHERE id = ?", [instance.id])

            conn.commit()
        finally:
            self._pending_new = []
            self._pending_dirty = []
            self._pending_delete = []

    def rollback(self):
        self._pending_new = []
        self._pending_dirty = []
        self._pending_delete = []
        self.db.connection.rollback()


class SQLAlchemy:
    """Minimal Flask-SQLAlchemy-compatible facade backed by sqlite3."""

    Model = Model
    Column = Column
    Integer = Integer
    String = String
    Text = Text
    Float = Float
    Boolean = Boolean
    DateTime = DateTime

    def __init__(self):
        self.connection = None
        self._lock = threading.Lock()
        self.session = None
        self.app = None

        # Bind these as attributes too so `db.Model` subclasses share state
        class _BoundModel(Model):
            pass

        _BoundModel._db = self
        self.Model = _BoundModel

    def init_app(self, app):
        self.app = app
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")
        path = uri.replace("sqlite:///", "") or ":memory:"
        if path != ":memory:":
            import os
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.session = _Session(self)
        self.Model._db = self

    def create_all(self):
        for model_cls in self._all_models(self.Model):
            self._create_table(model_cls)

    def _all_models(self, base):
        result = []
        for sub in base.__subclasses__():
            if hasattr(sub, "__tablename__"):
                result.append(sub)
            result.extend(self._all_models(sub))
        return result

    def _create_table(self, model_cls):
        cols_sql = []
        for name, col in model_cls._columns.items():
            parts = [name, col.type.sql_type]
            if col.primary_key:
                parts.append("PRIMARY KEY AUTOINCREMENT")
            if not col.nullable and not col.primary_key:
                parts.append("NOT NULL")
            if col.unique:
                parts.append("UNIQUE")
            cols_sql.append(" ".join(parts))
        ddl = f"CREATE TABLE IF NOT EXISTS {model_cls.__tablename__} ({', '.join(cols_sql)})"
        self.connection.execute(ddl)
        self.connection.commit()

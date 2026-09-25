import os

os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-testing-0123456789abcdef"
os.environ["ENCRYPTION_KEY"] = "DY8rzqi2m1_S4zsK6EpTfc7qKiXIlsn4yypAo-61DtM="
os.environ["MCP_API_KEY"] = "test-mcp-key"
os.environ["MCP_ENABLED"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_USE_MOCK"] = "true"

import sqlalchemy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite cannot compile Postgres-only JSONB. Patch the type BEFORE any model
# module is imported so Column(JSONB, ...) picks up the portable JSON type.
import sqlalchemy.dialects.postgresql as _pg

_pg.JSONB = sqlalchemy.JSON

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.role import Role, RolePermission
from app.models.permission import Permission
from app.models.connection import DatabaseConnection
from app.models.dashboard import Dashboard
from app.utils.security import get_password_hash, create_access_token


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_permission(db, name):
    perm = Permission(name=name, resource=name.split(".")[0], action=name.split(".")[1], description=name)
    db.add(perm)
    db.commit()
    return perm


def _make_role(db, name, permissions=None, is_system=False):
    role = Role(name=name, description=name, is_system=is_system)
    db.add(role)
    db.commit()
    for perm in permissions or []:
        db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    return role


def _make_user(db, email, roles=None):
    user = User(email=email, password_hash=get_password_hash("Password123!"), full_name=email, is_active=True)
    db.add(user)
    db.commit()
    for role in roles or []:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    return user


@pytest.fixture()
def permissions(db_session):
    names = ["database.read", "database.create", "database.update", "database.delete",
             "database.test", "database.sync", "database.schema", "database.connect",
             "query.read", "query.execute", "query.delete", "dashboard.read", "dashboard.create",
             "dashboard.update", "dashboard.delete", "access.manage", "audit.read",
             "user.read", "user.create", "user.update", "user.delete", "role.read", "role.create",
             "role.update", "role.delete", "import.csv", "import.history", "export.pdf",
             "export.excel", "export.png", "export.csv"]
    return {n: _make_permission(db_session, n) for n in names}


@pytest.fixture()
def plain_user(db_session):
    return _make_user(db_session, "plain@test.com")


@pytest.fixture()
def analyst(db_session, permissions):
    role = _make_role(db_session, "Analyst", [permissions["database.read"], permissions["query.read"],
                                              permissions["query.execute"], permissions["dashboard.read"],
                                              permissions["dashboard.create"]])
    return _make_user(db_session, "analyst@test.com", [role])


@pytest.fixture()
def viewer(db_session, permissions):
    role = _make_role(db_session, "Viewer", [permissions["database.read"], permissions["dashboard.read"]])
    return _make_user(db_session, "viewer@test.com", [role])


@pytest.fixture()
def admin(db_session, permissions):
    role = _make_role(db_session, "SuperAdmin", list(permissions.values()))
    return _make_user(db_session, "admin@test.com", [role])


def auth_headers(user):
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def superadmin_roles(db_session):
    pass


@pytest.fixture()
def owned_connection(db_session, analyst):
    conn = DatabaseConnection(
        name="analyst-db", connection_type="postgresql", host="localhost",
        port=5432, database_name="analyst_db", username="u",
        password="plaintext-legacy-password", created_by=analyst.id,
    )
    db_session.add(conn)
    db_session.commit()
    return conn

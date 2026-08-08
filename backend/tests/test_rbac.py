import pytest

from app.api.deps import user_has_permission
from tests.conftest import auth_headers


class TestRBACPermissions:
    def test_user_without_roles_has_no_permissions(self, db_session, plain_user):
        assert user_has_permission(db_session, plain_user, "database.read") is False

    def test_user_with_role_holding_permission_has_it(self, db_session, analyst):
        assert user_has_permission(db_session, analyst, "database.read") is True

    def test_user_lacking_permission_denied(self, db_session, analyst):
        assert user_has_permission(db_session, analyst, "access.manage") is False

    def test_admin_has_access_manage(self, db_session, admin):
        assert user_has_permission(db_session, admin, "access.manage") is True


class TestRBACApiGates:
    def test_unauthenticated_gets_401_or_403(self, client):
        r = client.get("/api/v1/connections")
        assert r.status_code in (401, 403)

    def test_plain_user_cannot_list_connections(self, client, plain_user):
        r = client.get("/api/v1/connections", headers=auth_headers(plain_user))
        assert r.status_code == 403
        assert "Insufficient permissions" in r.json()["detail"]

    def test_analyst_can_list_own_connections(self, client, analyst, owned_connection):
        r = client.get("/api/v1/connections", headers=auth_headers(analyst))
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_analyst_cannot_assign_roles(self, client, analyst, admin):
        r = client.post(
            f"/api/v1/users/{admin.id}/roles",
            json={"role_id": 1},
            headers=auth_headers(analyst),
        )
        assert r.status_code == 403

    def test_analyst_cannot_read_audit_logs(self, client, analyst):
        r = client.get("/api/v1/audit/logs", headers=auth_headers(analyst))
        assert r.status_code == 403

    def test_admin_can_read_audit_logs(self, client, admin):
        r = client.get("/api/v1/audit/logs", headers=auth_headers(admin))
        assert r.status_code == 200

    def test_analyst_cannot_create_database(self, client, analyst):
        r = client.post(
            "/api/v1/connections",
            json={
                "name": "x", "connection_type": "postgresql", "host": "h",
                "port": 5432, "database_name": "d", "username": "u", "password": "p",
            },
            headers=auth_headers(analyst),
        )
        assert r.status_code == 403

    def test_admin_can_create_database(self, client, admin):
        r = client.post(
            "/api/v1/connections",
            json={
                "name": "x", "connection_type": "postgresql", "host": "h",
                "port": 5432, "database_name": "d", "username": "u", "password": "p",
            },
            headers=auth_headers(admin),
        )
        assert r.status_code == 201


class TestSystemRoleProtection:
    def test_system_role_cannot_be_deleted(self, client, admin, db_session):
        from app.models.role import Role

        role = Role(name="SystemRole", description="x", is_system=True)
        db_session.add(role)
        db_session.commit()
        r = client.delete(f"/api/v1/roles/{role.id}", headers=auth_headers(admin))
        assert r.status_code == 400
        assert "System roles" in r.json()["detail"]

    def test_system_role_cannot_be_modified(self, client, admin, db_session):
        from app.models.role import Role

        role = Role(name="SystemRole2", description="x", is_system=True)
        db_session.add(role)
        db_session.commit()
        r = client.put(
            f"/api/v1/roles/{role.id}",
            json={"name": "Renamed"},
            headers=auth_headers(admin),
        )
        assert r.status_code == 400

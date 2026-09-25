from app.services import connection_service, dashboard_service
from tests.conftest import auth_headers


class TestConnectionOwnership:
    def test_get_database_scoped_to_owner(self, db_session, owned_connection, analyst, plain_user):
        assert connection_service.get_database(
            db_session, owned_connection.id, user_id=plain_user.id,
        ) is None
        assert connection_service.get_database(
            db_session, owned_connection.id, user_id=analyst.id,
        ) is not None

    def test_admin_with_access_manage_sees_other_users_connections(
        self, db_session, owned_connection, admin,
    ):
        assert connection_service.get_database(
            db_session, owned_connection.id, user_id=admin.id, include_all=True,
        ) is not None

    def test_list_scoped_to_owner(self, db_session, owned_connection, analyst, plain_user):
        _, total = connection_service.list_databases(
            db_session, user_id=plain_user.id,
        )
        assert total == 0
        _, total = connection_service.list_databases(
            db_session, user_id=analyst.id,
        )
        assert total == 1

    def test_api_404_on_other_users_connection(self, client, owned_connection, viewer):
        r = client.get(
            f"/api/v1/connections/{owned_connection.id}",
            headers=auth_headers(viewer),
        )
        assert r.status_code == 404


class TestDashboardOwnership:
    def test_get_dashboard_scoped_to_owner(self, db_session, analyst, plain_user):
        from app.models.dashboard import Dashboard

        dash = Dashboard(title="My dash", user_id=analyst.id)
        db_session.add(dash)
        db_session.commit()

        assert dashboard_service.get_dashboard(
            db_session, dash.id, user_id=plain_user.id,
        ) is None
        assert dashboard_service.get_dashboard(
            db_session, dash.id, user_id=analyst.id,
        ) is not None

    def test_api_404_on_other_users_dashboard(self, client, db_session, analyst, viewer):
        from app.models.dashboard import Dashboard

        dash = Dashboard(title="Private", user_id=analyst.id)
        db_session.add(dash)
        db_session.commit()

        r = client.get(f"/api/v1/dashboards/{dash.id}", headers=auth_headers(viewer))
        assert r.status_code == 404

        r = client.get(f"/api/v1/dashboards/{dash.id}", headers=auth_headers(analyst))
        assert r.status_code == 200

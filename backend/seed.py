"""Seed script to create initial roles, permissions, and admin user."""
import os
import secrets

import time

from sqlalchemy import inspect, text

from app.database import SessionLocal, engine, Base
import app.models
from app.models.user import User, UserRole
from app.models.role import Role, RolePermission
from app.models.permission import Permission
from app.utils.security import get_password_hash


def wait_for_db(max_retries: int = 20, delay: float = 2.0):
    """Wait for database engine to accept connections before running migrations/seeding."""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                return
        except Exception as exc:
            print(f"[seed] Database not ready yet (attempt {attempt}/{max_retries}): {exc}")
            if attempt == max_retries:
                raise
            time.sleep(delay)


def _ensure_columns():
    """Add columns that may be missing on existing tables."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description VARCHAR(500),
                owner_id INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            );
        """))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP WITH TIME ZONE"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT"))
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.execute(text("ALTER TABLE users ALTER COLUMN avatar_url TYPE TEXT"))
        conn.execute(text("ALTER TABLE database_connections ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.execute(text("ALTER TABLE dashboards ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.execute(text("ALTER TABLE queries ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.execute(text("ALTER TABLE query_templates ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.execute(text("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS company_id INTEGER"))
        conn.commit()

        # If any companies don't exist yet, seed a default company for legacy users
        res = conn.execute(text("SELECT id FROM companies LIMIT 1")).fetchone()
        if not res:
            conn.execute(text("INSERT INTO companies (name, description, owner_id) VALUES ('Default Company', 'Primary organization', 1)"))
            conn.commit()
            default_company_id = conn.execute(text("SELECT id FROM companies LIMIT 1")).scalar()
            conn.execute(text(f"UPDATE users SET company_id = {default_company_id} WHERE company_id IS NULL"))
            conn.execute(text(f"UPDATE database_connections SET company_id = {default_company_id} WHERE company_id IS NULL"))
            conn.execute(text(f"UPDATE dashboards SET company_id = {default_company_id} WHERE company_id IS NULL"))
            conn.execute(text(f"UPDATE queries SET company_id = {default_company_id} WHERE company_id IS NULL"))
            conn.commit()


def seed():
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    db = SessionLocal()

    try:
        # Create permissions
        permissions_data = [
            # Database permissions
            ("database.create", "database", "create", "Create new database connections"),
            ("database.read", "database", "read", "View database connections"),
            ("database.update", "database", "update", "Update database connections"),
            ("database.delete", "database", "delete", "Delete database connections"),
            ("database.test", "database", "test", "Test database connections"),
            ("database.sync", "database", "sync", "Sync database schemas"),
            ("database.schema", "database", "schema", "View database schemas"),
            ("database.connect", "database", "connect", "Connect to databases"),
            # Query permissions
            ("query.execute", "query", "execute", "Execute SQL queries"),
            ("query.read", "query", "read", "View query history"),
            ("query.delete", "query", "delete", "Delete queries"),
            # Dashboard permissions
            ("dashboard.create", "dashboard", "create", "Create dashboards"),
            ("dashboard.read", "dashboard", "read", "View dashboards"),
            ("dashboard.update", "dashboard", "update", "Update dashboards"),
            ("dashboard.delete", "dashboard", "delete", "Delete dashboards"),
            # User management
            ("user.create", "user", "create", "Create users"),
            ("user.read", "user", "read", "View users"),
            ("user.update", "user", "update", "Update users"),
            ("user.delete", "user", "delete", "Delete users"),
            # Role management
            ("role.create", "role", "create", "Create roles"),
            ("role.read", "role", "read", "View roles"),
            ("role.update", "role", "update", "Update roles"),
            ("role.delete", "role", "delete", "Delete roles"),
            # Access management
            ("access.manage", "access", "manage", "Manage user access"),
            # Data import
            ("import.csv", "import", "csv", "Import CSV files"),
            ("import.history", "import", "history", "View import history"),
            # Export
            ("export.pdf", "export", "pdf", "Export to PDF"),
            ("export.excel", "export", "excel", "Export to Excel"),
            ("export.png", "export", "png", "Export to PNG"),
            # Audit
            ("audit.read", "audit", "read", "View audit logs"),
        ]

        for name, resource, action, desc in permissions_data:
            existing = db.query(Permission).filter(Permission.name == name).first()
            if not existing:
                db.add(Permission(name=name, resource=resource, action=action, description=desc))

        db.commit()

        # Create roles (SuperAdmin, Admin, Analyst, Viewer)
        roles_data = {
            "SuperAdmin": {
                "description": "Company owner with full unrestricted system access",
                "is_system": True,
            },
            "Admin": {
                "description": "Company administrator with user, database, query, and audit management",
                "is_system": True,
            },
            "Analyst": {
                "description": "Can create connections, query data and build dashboards",
                "is_system": True,
            },
            "Viewer": {
                "description": "Can view shared dashboards and reports",
                "is_system": True,
            },
        }

        all_permissions = {p.name: p.id for p in db.query(Permission).all()}

        for role_name, role_info in roles_data.items():
            existing_role = db.query(Role).filter(Role.name == role_name).first()
            if existing_role:
                role = existing_role
                role.description = role_info["description"]
                role.is_system = role_info["is_system"]
            else:
                role = Role(
                    name=role_name,
                    description=role_info["description"],
                    is_system=role_info["is_system"],
                )
                db.add(role)
                db.commit()
                db.refresh(role)

            # Assign permissions based on role
            if role_name == "SuperAdmin":
                perm_ids = list(all_permissions.values())
            elif role_name == "Admin":
                admin_perms = [
                    p for name, p in all_permissions.items()
                    if not name.startswith(("role.create", "role.delete", "role.update"))
                ]
                perm_ids = admin_perms
            elif role_name == "Analyst":
                analyst_perms = [
                    p for name, p in all_permissions.items()
                    if name.startswith(("database.", "query.", "dashboard.", "import.", "export."))
                ]
                perm_ids = analyst_perms
            elif role_name == "Viewer":
                viewer_perms = [p for name, p in all_permissions.items()
                               if name in ("database.read", "query.read", "dashboard.read")]
                perm_ids = viewer_perms
            else:
                perm_ids = []

            # Reconcile: grant any missing permissions on existing roles so a
            # seed rerun (or a seed that grew since first deploy) upgrades roles
            # without dropping existing grants.
            granted_ids = {
                rp.permission_id
                for rp in db.query(RolePermission)
                .filter(RolePermission.role_id == role.id)
                .all()
            }
            for pid in perm_ids:
                if pid not in granted_ids:
                    db.add(RolePermission(role_id=role.id, permission_id=pid))

        db.commit()

        # Create initial SuperAdmin user if not exists
        superadmin_role = db.query(Role).filter(Role.name == "SuperAdmin").first()
        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        analyst_role = db.query(Role).filter(Role.name == "Analyst").first()
        viewer_role = db.query(Role).filter(Role.name == "Viewer").first()

        admin_email = os.environ.get("ADMIN_EMAIL") or os.environ.get("FIRST_SUPERUSER") or "admin@agentic.com"
        admin_name = os.environ.get("ADMIN_NAME") or os.environ.get("FIRST_SUPERUSER_NAME") or "System Admin"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            # Prefer ADMIN_PASSWORD from the environment; otherwise generate a
            # strong random one. Never use a hardcoded default.
            admin_password = os.environ.get("ADMIN_PASSWORD") or os.environ.get("FIRST_SUPERUSER_PASSWORD") or secrets.token_urlsafe(12)
            from app.models.company import Company
            default_company = db.query(Company).first()
            company_id = default_company.id if default_company else None
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                full_name=admin_name,
                company_id=company_id,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

            if default_company and not default_company.owner_id:
                default_company.owner_id = admin.id
                db.commit()

            # Assign SuperAdmin role to initial system admin
            if superadmin_role:
                db.add(UserRole(user_id=admin.id, role_id=superadmin_role.id))
                db.commit()

        # Reconcile user roles for all existing users: company owner is SuperAdmin
        from app.models.company import Company
        all_companies = db.query(Company).all()
        for comp in all_companies:
            if comp.owner_id and superadmin_role:
                owner_has_superadmin = db.query(UserRole).filter(
                    UserRole.user_id == comp.owner_id,
                    UserRole.role_id == superadmin_role.id,
                ).first()
                if not owner_has_superadmin:
                    db.add(UserRole(user_id=comp.owner_id, role_id=superadmin_role.id))
        db.commit()

        print("Seed completed successfully!")
        if not existing_admin:
            print(f"Admin login: {admin_email} / {admin_password}")
        else:
            print("Admin user already exists (password not changed)")

    finally:
        db.close()


if __name__ == "__main__":
    seed()

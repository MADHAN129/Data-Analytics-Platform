"""Seed script to create initial roles, permissions, and admin user."""
import os
import secrets

from sqlalchemy import inspect, text

from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.role import Role, RolePermission
from app.models.permission import Permission
from app.utils.security import get_password_hash


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

        # Create roles (SuperAdmin, Analyst, Viewer)
        roles_data = {
            "SuperAdmin": {
                "description": "Full system access with all permissions",
                "is_system": True,
            },
            "Analyst": {
                "description": "Can query data and create dashboards",
                "is_system": True,
            },
            "Viewer": {
                "description": "Can view dashboards and reports",
                "is_system": True,
            },
        }

        all_permissions = {p.name: p.id for p in db.query(Permission).all()}

        for role_name, role_info in roles_data.items():
            existing_role = db.query(Role).filter(Role.name == role_name).first()
            if existing_role:
                role = existing_role
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

        # Clean up legacy 'Admin' role if present and migrate users to SuperAdmin
        superadmin_role = db.query(Role).filter(Role.name == "SuperAdmin").first()
        legacy_admin_role = db.query(Role).filter(Role.name == "Admin").first()
        if legacy_admin_role and superadmin_role:
            admin_user_roles = db.query(UserRole).filter(UserRole.role_id == legacy_admin_role.id).all()
            for aur in admin_user_roles:
                has_superadmin = db.query(UserRole).filter(
                    UserRole.user_id == aur.user_id,
                    UserRole.role_id == superadmin_role.id,
                ).first()
                if not has_superadmin:
                    db.add(UserRole(user_id=aur.user_id, role_id=superadmin_role.id))
            db.query(UserRole).filter(UserRole.role_id == legacy_admin_role.id).delete()
            db.query(RolePermission).filter(RolePermission.role_id == legacy_admin_role.id).delete()
            db.query(Role).filter(Role.id == legacy_admin_role.id).delete()
            db.commit()

        # Create admin user if not exists
        superadmin_role = db.query(Role).filter(Role.name == "SuperAdmin").first()
        analyst_role = db.query(Role).filter(Role.name == "Analyst").first()
        admin_email = "admin@agentic.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            # Prefer ADMIN_PASSWORD from the environment; otherwise generate a
            # strong random one. Never use a hardcoded default.
            admin_password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
            admin = User(
                email=admin_email,
                password_hash=get_password_hash(admin_password),
                full_name="System Admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)

            # Assign SuperAdmin role
            if superadmin_role:
                db.add(UserRole(user_id=admin.id, role_id=superadmin_role.id))
                db.commit()

        # Reconcile user roles for all existing users so they hold proper clean permissions
        viewer_role = db.query(Role).filter(Role.name == "Viewer").first()
        all_users = db.query(User).all()
        for user in all_users:
            user_roles = [ur.role_id for ur in db.query(UserRole).filter(UserRole.user_id == user.id).all()]
            is_admin_user = (
                user.email.lower().startswith("admin@")
                or (user.full_name and "admin" in user.full_name.lower())
            )
            if is_admin_user and superadmin_role:
                if superadmin_role.id not in user_roles:
                    db.add(UserRole(user_id=user.id, role_id=superadmin_role.id))
                # Remove redundant lower roles
                if viewer_role and viewer_role.id in user_roles:
                    db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == viewer_role.id).delete()
                if analyst_role and analyst_role.id in user_roles:
                    db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == analyst_role.id).delete()
            elif analyst_role and (not superadmin_role or superadmin_role.id not in user_roles):
                if analyst_role.id not in user_roles:
                    db.add(UserRole(user_id=user.id, role_id=analyst_role.id))
                # Remove redundant viewer role if analyst
                if viewer_role and viewer_role.id in user_roles:
                    db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.role_id == viewer_role.id).delete()

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

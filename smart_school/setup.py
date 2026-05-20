import frappe


SMART_SCHOOL_ROLES = [
    {
        "role_name": "Parent",
        "desk_access": 0,
        "description": "Parent / Guardian of one or more students. Read-only access via mobile/web apps.",
    },
    {
        "role_name": "Teacher",
        "desk_access": 0,
        "description": "Teaching staff. Marks attendance, posts announcements, views own schedule.",
    },
    {
        "role_name": "School Admin",
        "desk_access": 1,
        "description": "School-level administrator. Manages admissions, fees, timetable and calendar.",
    },
]


def after_install():
    """Run once when the app is installed."""
    ensure_roles()


def after_migrate():
    """Run on every bench migrate so new roles arrive on existing benches too."""
    ensure_roles()


def ensure_roles():
    """Create Smart School roles if they don't already exist."""
    for role in SMART_SCHOOL_ROLES:
        if frappe.db.exists("Role", role["role_name"]):
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "Role",
                "role_name": role["role_name"],
                "desk_access": role["desk_access"],
                "description": role["description"],
            })
            doc.insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to create role {role['role_name']}: {e}", "Smart School Setup")

    frappe.db.commit()

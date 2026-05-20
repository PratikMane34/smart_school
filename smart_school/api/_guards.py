import frappe
from frappe import _


# ─────────────────────────────────────────────
# Role gate
# ─────────────────────────────────────────────

def require_role(*roles):
    """Raise PermissionError if the current user has none of <roles>.

    System Manager and Administrator are always allowed through.
    Call this at the top of an endpoint:

        def my_endpoint():
            require_role("School Admin")
            ...
    """
    if frappe.session.user == "Administrator":
        return

    user_roles = set(frappe.get_roles())
    if "System Manager" in user_roles:
        return

    if not user_roles.intersection(roles):
        frappe.throw(
            _("You don't have permission to perform this action."),
            frappe.PermissionError
        )


# ─────────────────────────────────────────────
# Parent-of relationship
# ─────────────────────────────────────────────

def assert_parent_of(student):
    """Raise PermissionError if the current user is not a guardian of <student>.

    System Manager and School Admin always pass.
    """
    if not student:
        frappe.throw(_("Student is required."))

    if frappe.session.user == "Administrator":
        return

    user_roles = set(frappe.get_roles())
    if user_roles.intersection({"System Manager", "School Admin"}):
        return

    user = frappe.session.user

    guardian_names = frappe.get_all(
        "Guardian",
        filters={"user": user},
        pluck="name"
    )
    if not guardian_names:
        guardian_names = frappe.get_all(
            "Guardian",
            filters={"email_address": user},
            pluck="name"
        )

    if not guardian_names:
        frappe.throw(
            _("You are not registered as a guardian for any student."),
            frappe.PermissionError
        )

    is_guardian = frappe.db.exists(
        "Student Guardian",
        {"parent": student, "guardian": ["in", guardian_names]}
    )

    if not is_guardian:
        frappe.throw(
            _("You are not authorised to access this student's record."),
            frappe.PermissionError
        )


# ─────────────────────────────────────────────
# Teacher-of-group relationship
# ─────────────────────────────────────────────

def assert_teacher_of_group(student_group):
    """Raise PermissionError if the current user is not listed as an instructor
    on <student_group>.

    Resolution: current user -> Employee (via user_id) -> Instructor (via employee)
    -> Student Group Instructor row on <student_group>.

    System Manager and School Admin always pass.
    """
    if not student_group:
        frappe.throw(_("Student Group is required."))

    if frappe.session.user == "Administrator":
        return

    user_roles = set(frappe.get_roles())
    if user_roles.intersection({"System Manager", "School Admin"}):
        return

    user = frappe.session.user

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if not employee:
        frappe.throw(
            _("You are not linked to any Employee record."),
            frappe.PermissionError
        )

    instructor_names = frappe.get_all(
        "Instructor",
        filters={"employee": employee},
        pluck="name"
    )
    if not instructor_names:
        frappe.throw(
            _("You are not linked to any Instructor record."),
            frappe.PermissionError
        )

    is_instructor = frappe.db.exists(
        "Student Group Instructor",
        {"parent": student_group, "instructor": ["in", instructor_names]}
    )

    if not is_instructor:
        frappe.throw(
            _("You are not authorised to take action on this student group."),
            frappe.PermissionError
        )


# ─────────────────────────────────────────────
# Convenience helper used by enrichment / listings
# ─────────────────────────────────────────────

def current_user_guardian_names():
    """Return the list of Guardian doc names for the current user, if any."""
    user = frappe.session.user
    if not user or user == "Guest":
        return []

    names = frappe.get_all("Guardian", filters={"user": user}, pluck="name")
    if not names:
        names = frappe.get_all("Guardian", filters={"email_address": user}, pluck="name")
    return names

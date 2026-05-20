import frappe
from smart_school.api._guards import require_role


# ─────────────────────────────────────────────
# Announcement - read
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_announcements(audience=None, class_name=None, role=None, student_group=None,
                     active_only=1, start_page=1, page_size=20):
    """
    List announcements. By default returns active announcements (valid_to in
    the future or not set).

    GET /api/method/smart_school.api.messaging.get_announcements
    Query params: audience, class_name, role, student_group, active_only,
                  start_page, page_size
    """
    filters = []
    if audience:
        filters.append(["audience", "=", audience])
    if class_name:
        filters.append(["class", "=", class_name])
    if role:
        filters.append(["role", "=", role])
    if student_group:
        filters.append(["student_group", "=", student_group])

    or_filters = None
    if int(active_only or 0):
        today = frappe.utils.nowdate()
        filters.append(["valid_from", "<=", today])
        or_filters = [
            ["valid_to", ">=", today],
            ["valid_to", "is", "not set"],
        ]

    start_page = int(start_page)
    page_size = int(page_size)

    announcements = frappe.get_all(
        "Announcement",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "title", "body", "audience", "class", "role",
                "student_group", "valid_from", "valid_to", "attachment",
                "posted_by", "creation", "modified"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="creation desc"
    )

    for a in announcements:
        if a.get("attachment"):
            a["attachment"] = frappe.utils.get_url() + a["attachment"]

    return {
        "success": True,
        "message": "Announcements fetched successfully",
        "data": announcements
    }


@frappe.whitelist()
def get_announcement(name=None):
    """Fetch a single announcement by name."""
    if not name:
        frappe.throw("Announcement name is required")

    ann = frappe.get_doc("Announcement", name)
    data = ann.as_dict()
    if data.get("attachment"):
        data["attachment"] = frappe.utils.get_url() + data["attachment"]

    return {
        "success": True,
        "message": "Announcement fetched successfully",
        "data": data
    }


# ─────────────────────────────────────────────
# Announcement - write
# ─────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_announcement():
    """
    Create an announcement. Teachers can post (their own write permission on
    the doctype handles this); School Admin can post for any audience.

    POST /api/method/smart_school.api.messaging.create_announcement
    Body: {
        "title": "School closed tomorrow",
        "body": "<p>Due to heavy rainfall...</p>",
        "audience": "All",
        "valid_from": "2026-05-21",
        "valid_to": "2026-05-22"
    }
    """
    require_role("School Admin", "Teacher")

    data = frappe.request.get_json() or {}

    if not (data.get("title") and data.get("body")):
        frappe.throw("title and body are required")

    ann = frappe.get_doc({
        "doctype": "Announcement",
        "title": data.get("title"),
        "body": data.get("body"),
        "audience": data.get("audience") or "All",
        "class": data.get("class"),
        "role": data.get("role"),
        "student_group": data.get("student_group"),
        "valid_from": data.get("valid_from") or frappe.utils.nowdate(),
        "valid_to": data.get("valid_to"),
        "attachment": data.get("attachment"),
        "posted_by": frappe.session.user,
    })
    ann.insert()

    return {
        "success": True,
        "message": "Announcement created successfully",
        "data": ann.name
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_announcement():
    """Update fields on an existing announcement."""
    data = frappe.request.get_json() or {}
    if not data.get("name"):
        frappe.throw("Announcement name is required")

    doc = frappe.get_doc("Announcement", data.get("name"))

    if doc.posted_by != frappe.session.user:
        require_role("School Admin")

    updatable = ["title", "body", "audience", "class", "role",
                 "student_group", "valid_from", "valid_to", "attachment"]
    for f in updatable:
        if f in data:
            doc.set(f, data.get(f))

    doc.save()

    return {
        "success": True,
        "message": "Announcement updated successfully",
        "data": doc.name
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_announcement(name=None):
    """Delete an announcement."""
    if not name:
        frappe.throw("Announcement name is required")

    doc = frappe.get_doc("Announcement", name)
    if doc.posted_by != frappe.session.user:
        require_role("School Admin")

    frappe.delete_doc("Announcement", name)
    return {
        "success": True,
        "message": "Announcement deleted successfully",
        "data": name
    }

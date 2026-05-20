import frappe
from smart_school.api._guards import require_role


# ─────────────────────────────────────────────
# School Event - read
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_events(from_date=None, to_date=None, event_type=None, class_name=None,
              audience=None, start_page=1, page_size=50):
    """
    List School Events for a date range.

    GET /api/method/smart_school.api.calendar.get_events
    Query params: from_date, to_date, event_type, class_name, audience,
                  start_page, page_size
    """
    filters = []

    # Event overlaps the requested window when:
    #   start_date <= to_date AND (end_date >= from_date OR end_date is null)
    # We model the OR-on-end_date via or_filters below.
    or_filters = None
    if from_date and to_date:
        filters.append(["start_date", "<=", to_date])
        or_filters = [
            ["end_date", ">=", from_date],
            ["end_date", "is", "not set"],
        ]
    elif from_date:
        or_filters = [
            ["start_date", ">=", from_date],
            ["end_date", ">=", from_date],
        ]
    elif to_date:
        filters.append(["start_date", "<=", to_date])

    if event_type:
        filters.append(["event_type", "=", event_type])
    if audience:
        filters.append(["audience", "=", audience])
    if class_name:
        filters.append(["class", "=", class_name])

    start_page = int(start_page)
    page_size = int(page_size)

    events = frappe.get_all(
        "School Event",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "title", "event_type", "start_date", "end_date",
                "all_day", "audience", "class", "role", "student_group",
                "description", "attachment"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="start_date asc"
    )

    for e in events:
        if e.get("attachment"):
            e["attachment"] = frappe.utils.get_url() + e["attachment"]

    return {
        "success": True,
        "message": "School events fetched successfully",
        "data": events
    }


@frappe.whitelist()
def get_event(name=None):
    """Fetch a single School Event by name."""
    if not name:
        frappe.throw("School Event name is required")

    event = frappe.get_doc("School Event", name)

    return {
        "success": True,
        "message": "School event fetched successfully",
        "data": event.as_dict()
    }


# ─────────────────────────────────────────────
# School Event - write (admin only)
# ─────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def create_event():
    """
    Create a School Event.

    POST /api/method/smart_school.api.calendar.create_event
    Body: {
        "title": "Annual Sports Day",
        "event_type": "Event",
        "start_date": "2026-08-15",
        "end_date": "2026-08-15",
        "all_day": 1,
        "audience": "All",
        "description": "..."
    }
    """
    require_role("School Admin")

    data = frappe.request.get_json() or {}

    event = frappe.get_doc({
        "doctype": "School Event",
        "title": data.get("title"),
        "event_type": data.get("event_type"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "all_day": 1 if data.get("all_day", 1) else 0,
        "audience": data.get("audience") or "All",
        "class": data.get("class"),
        "role": data.get("role"),
        "student_group": data.get("student_group"),
        "description": data.get("description"),
        "attachment": data.get("attachment"),
    })
    event.insert()

    return {
        "success": True,
        "message": "School event created successfully",
        "data": event.name
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_event():
    """Update fields on an existing School Event."""
    require_role("School Admin")

    data = frappe.request.get_json() or {}
    if not data.get("name"):
        frappe.throw("School Event name is required")

    doc = frappe.get_doc("School Event", data.get("name"))

    updatable = ["title", "event_type", "start_date", "end_date", "all_day",
                 "audience", "class", "role", "student_group",
                 "description", "attachment"]
    for f in updatable:
        if f in data:
            doc.set(f, data.get(f))

    doc.save()

    return {
        "success": True,
        "message": "School event updated successfully",
        "data": doc.name
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_event(name=None):
    """Delete a School Event."""
    require_role("School Admin")

    if not name:
        frappe.throw("School Event name is required")

    frappe.delete_doc("School Event", name)
    return {
        "success": True,
        "message": "School event deleted successfully",
        "data": name
    }

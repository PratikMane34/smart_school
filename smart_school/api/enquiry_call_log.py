import frappe


@frappe.whitelist()
def get_enquiry_call_log(mobile=None, call_type=None, from_date=None, to_date=None,
                        start_page=1, page_size=20):
    """
    List Enquiry Call Logs with optional filters.

    Query params: mobile (contains), call_type, from_date, to_date,
                  start_page, page_size
    """
    filters = {}
    if mobile:
        filters["mobile"] = ["like", f"%{mobile}%"]
    if call_type:
        filters["call_type"] = call_type
    if from_date and to_date:
        filters["call_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["call_date"] = [">=", from_date]
    elif to_date:
        filters["call_date"] = ["<=", to_date]

    start_page = int(start_page)
    page_size = int(page_size)

    call_logs = frappe.get_all(
        "Enquiry Call Logs",
        filters=filters,
        fields=["name", "enquirer_name", "mobile", "call_date", "next_followup_date",
                "call_duration", "description", "note", "call_type"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="call_date desc"
    )

    total = frappe.db.count("Enquiry Call Logs", filters=filters)

    return {
        "success": True,
        "message": "Enquiry call logs fetched successfully",
        "data": call_logs,
        "total": total,
        "start_page": start_page,
        "page_size": page_size
    }


@frappe.whitelist(methods=["POST"])
def call_logs():
    data = frappe.request.get_json() or {}
    log = frappe.get_doc({
        "doctype": "Enquiry Call Logs",
        "enquirer_name": data.get("enquirer_name"),
        "mobile": data.get("mobile"),
        "call_date": data.get("call_date"),
        "description": data.get("description"),
        "next_followup_date": data.get("next_followup_date"),
        "call_duration": data.get("call_duration"),
        "note": data.get("note"),
        "call_type": data.get("call_type")
    })
    log.insert()
    return {
        "success": True,
        "message": "Call log created successfully",
        "data": log.name
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_call_log():
    data = frappe.request.get_json() or {}

    if not data.get("name"):
        frappe.throw("Document name is required")

    doc = frappe.get_doc("Enquiry Call Logs", data.get("name"))

    updatable_fields = [
        "enquirer_name", "mobile", "call_date", "description",
        "next_followup_date", "call_duration", "note", "call_type"
    ]
    for field in updatable_fields:
        if field in data:
            doc.set(field, data.get(field))

    doc.save()

    return {
        "success": True,
        "message": "Call log updated successfully",
        "data": doc.name
    }


# ─────────────────────────────────────────────
# Scheduler - daily follow-up reminders
# ─────────────────────────────────────────────

def send_followup_reminders():
    """
    Daily job: create a ToDo for the assigned user (or System Manager fallback)
    for every Admission Enquiry / Enquiry Call Log whose next_followup_date is
    today.

    Wired up in hooks.py under scheduler_events.daily.
    """
    today = frappe.utils.nowdate()

    enquiries = frappe.get_all(
        "Admission Enquiry",
        filters={"next_followup_date": today, "status": ["!=", "Dead"]},
        fields=["name", "name1", "assigned_to", "mobile_no"]
    )
    for e in enquiries:
        _create_followup_todo(
            reference_type="Admission Enquiry",
            reference_name=e.name,
            owner=e.assigned_to,
            description=f"Follow up with {e.name1 or e.name} ({e.mobile_no or 'no phone'})"
        )

    call_logs = frappe.get_all(
        "Enquiry Call Logs",
        filters={"next_followup_date": today},
        fields=["name", "enquirer_name", "mobile"]
    )
    for c in call_logs:
        _create_followup_todo(
            reference_type="Enquiry Call Logs",
            reference_name=c.name,
            owner=None,
            description=f"Follow up call with {c.enquirer_name or c.name} ({c.mobile or 'no phone'})"
        )


def _create_followup_todo(reference_type, reference_name, owner, description):
    """Create a ToDo only if one doesn't already exist for the same reference today."""
    existing = frappe.db.exists(
        "ToDo",
        {
            "reference_type": reference_type,
            "reference_name": reference_name,
            "status": "Open",
            "date": frappe.utils.nowdate(),
        }
    )
    if existing:
        return

    todo = frappe.get_doc({
        "doctype": "ToDo",
        "allocated_to": owner or "Administrator",
        "reference_type": reference_type,
        "reference_name": reference_name,
        "description": description,
        "date": frappe.utils.nowdate(),
        "priority": "Medium",
        "status": "Open",
    })
    todo.insert(ignore_permissions=True)

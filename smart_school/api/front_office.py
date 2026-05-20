import frappe
from smart_school.api._guards import require_role


# ─────────────────────────────────────────────
# Visitor
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_visitor_data():
    """
    Get the visitor data for the current user.
    """
    visitor = frappe.get_all(
        "Visitor",
        fields=["name", "visitor_name", "visitor_intime", "visitor_outtime",
                "visitor_purpose", "contact_number", "meeting_with", "id_card",
                "number_of_person", "attach_document", "note"]
    )
    for v in visitor:
        v.attach_document = (frappe.utils.get_url() + v.attach_document) if v.attach_document else None
    return {
        "success": True,
        "message": "Visitor data fetched successfully",
        "data": visitor
    }


@frappe.whitelist(methods=["POST"])
def create_visitor():
    """
    Create a new visitor.
    sample request:
    {
        "visitor_name": "John Doe",
        "visitor_intime": "2026-04-13 10:00:00",
        "visitor_outtime": "2026-04-13 11:00:00",
        "visitor_purpose": "Meeting",
        "contact_number": "1234567890",
        "meeting_with": "John Doe"
    }
    """
    data = frappe.request.get_json() or {}
    visitor = frappe.get_doc({
        "doctype": "Visitor",
        "visitor_name": data.get("visitor_name"),
        "visitor_intime": data.get("visitor_intime"),
        "visitor_outtime": data.get("visitor_outtime"),
        "visitor_purpose": data.get("visitor_purpose"),
        "contact_number": data.get("contact_number"),
        "meeting_with": data.get("meeting_with"),
        "id_card": data.get("id_card"),
        "number_of_person": data.get("number_of_person"),
        "attach_document": data.get("attach_document"),
        "note": data.get("note"),
    })
    visitor.insert()
    return {
        "success": True,
        "message": "Visitor created successfully",
        "data": visitor.visitor_name
    }


# ─────────────────────────────────────────────
# Admission Enquiry
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_admission_enquiry(status=None, source=None, assigned_to=None, class_name=None,
                          mobile=None, from_date=None, to_date=None,
                          start_page=1, page_size=20):
    """
    List admission enquiries with optional filters and pagination.

    GET /api/method/smart_school.api.front_office.get_admission_enquiry
    Query params: status, source, assigned_to, class (as class_name), mobile,
                  from_date, to_date, start_page, page_size
    """
    filters = {}
    if status:
        filters["status"] = status
    if source:
        filters["source"] = source
    if assigned_to:
        filters["assigned_to"] = assigned_to
    if class_name:
        filters["class"] = class_name
    if mobile:
        filters["mobile_no"] = ["like", f"%{mobile}%"]
    if from_date and to_date:
        filters["enquiry_date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["enquiry_date"] = [">=", from_date]
    elif to_date:
        filters["enquiry_date"] = ["<=", to_date]

    start_page = int(start_page)
    page_size = int(page_size)

    enquiry = frappe.get_all(
        "Admission Enquiry",
        filters=filters,
        fields=["name", "name1", "address", "enquiry_date", "reference",
                "no_of_children", "mobile_no", "description", "next_followup_date",
                "source", "email", "note", "status", "class", "assigned_to"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="modified desc"
    )

    total = frappe.db.count("Admission Enquiry", filters=filters)

    return {
        "success": True,
        "message": "Admission enquiry data fetched successfully",
        "data": enquiry,
        "total": total,
        "start_page": start_page,
        "page_size": page_size
    }


@frappe.whitelist(methods=["POST"])
def create_admission_enquiry():
    """
    Create a new admission enquiry.
    sample request:
    {
        "name1": "John Doe",
        "address": "123 Main St, Anytown, USA",
        "enquiry_date": "2026-04-13",
        "reference": "1234567890",
        "no_of_children": 1,
        "mobile_no": "1234567890",
        "description": "I am interested in your school",
        "next_followup_date": "2026-04-13",
        "source": "Website",
        "email": "john.doe@example.com",
        "note": "..."
    }
    """
    data = frappe.request.get_json() or {}
    enquiry = frappe.get_doc({
        "doctype": "Admission Enquiry",
        "name1": data.get("name1"),
        "address": data.get("address"),
        "enquiry_date": data.get("enquiry_date"),
        "reference": data.get("reference"),
        "no_of_children": data.get("no_of_children"),
        "mobile_no": data.get("mobile_no"),
        "description": data.get("description"),
        "next_followup_date": data.get("next_followup_date"),
        "source": data.get("source"),
        "email": data.get("email"),
        "note": data.get("note"),
        "status": data.get("status") or "Active",
        "class": data.get("class"),
        "assigned_to": data.get("assigned_to"),
    })
    enquiry.insert()
    return {
        "success": True,
        "message": "Admission enquiry created successfully",
        "data": enquiry.name
    }


@frappe.whitelist(methods=["PUT", "POST"])
def update_admission_enquiry():
    """
    Update fields on an existing Admission Enquiry. Only fields present in the
    request body are touched.

    sample request:
    { "name": "ADM-ENQ-0001", "status": "Passive", "next_followup_date": "2026-05-01" }
    """
    data = frappe.request.get_json() or {}

    if not data.get("name"):
        frappe.throw("Admission Enquiry name is required")

    doc = frappe.get_doc("Admission Enquiry", data.get("name"))

    updatable_fields = [
        "name1", "address", "enquiry_date", "reference", "no_of_children",
        "mobile_no", "description", "next_followup_date", "source", "email",
        "note", "status", "class", "assigned_to"
    ]
    for field in updatable_fields:
        if field in data:
            doc.set(field, data.get(field))

    doc.save()

    return {
        "success": True,
        "message": "Admission enquiry updated successfully",
        "data": doc.name
    }


@frappe.whitelist(methods=["DELETE", "POST"])
def delete_admission_enquiry(name=None):
    """
    Delete an Admission Enquiry by name.
    """
    if not name:
        frappe.throw("Admission Enquiry name is required")

    require_role("School Admin")

    frappe.delete_doc("Admission Enquiry", name)
    return {
        "success": True,
        "message": "Admission enquiry deleted successfully",
        "data": name
    }


@frappe.whitelist(methods=["POST"])
def convert_enquiry_to_applicant(name=None):
    """
    Create a Student Applicant from an existing Admission Enquiry.

    Marks the source enquiry as 'Passive' once converted.

    POST /api/method/smart_school.api.front_office.convert_enquiry_to_applicant
    Body: { "name": "ADM-ENQ-0001" }
    """
    if not name:
        frappe.throw("Admission Enquiry name is required")

    require_role("School Admin")

    enquiry = frappe.get_doc("Admission Enquiry", name)

    # name1 holds the enquirer's full name; best-effort split into first/last.
    first_name, _sep, last_name = (enquiry.name1 or "").partition(" ")
    if not first_name:
        first_name = "Applicant"

    applicant = frappe.get_doc({
        "doctype": "Student Applicant",
        "first_name": first_name,
        "last_name": last_name or None,
        "student_email_id": enquiry.email,
        "student_mobile_number": enquiry.mobile_no,
        "application_date": frappe.utils.nowdate(),
        "application_status": "Applied",
        "custom_class": enquiry.get("class"),
        "custom_email": enquiry.email,
    })
    applicant.insert(ignore_permissions=False)

    enquiry.status = "Passive"
    enquiry.save()

    return {
        "success": True,
        "message": "Admission enquiry converted to Student Applicant",
        "data": {
            "enquiry": enquiry.name,
            "applicant": applicant.name
        }
    }

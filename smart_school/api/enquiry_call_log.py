import frappe

@frappe.whitelist()
def get_enquiry_call_log():
    print("-------------------------------------")
    call_logs = frappe.get_all("Enquiry Call Logs",fields=["enquirer_name","mobile","call_date","next_followup_date","call_duration","description","note","call_type"])
    print(call_logs)
    return call_logs

@frappe.whitelist(methods="POST")
def call_logs():
    data = frappe.request.get_json()
    print("json data", data)
    visitor = frappe.get_doc({
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
    visitor.insert()
    return {
        "success": True,
        "message": "Visitor created successfully",
        "data": visitor.visitor_name
    }

@frappe.whitelist(methods=["PUT", "POST"])
def update_call_log():
    data = frappe.request.get_json()

    if not data.get("name"):
        frappe.throw("Document name is required")

    # Fetch existing doc
    doc = frappe.get_doc("Enquiry Call Logs", data.get("name"))

    # Update only provided fields
    if "enquirer_name" in data:
        doc.enquirer_name = data.get("enquirer_name")

    if "mobile" in data:
        doc.mobile = data.get("mobile")

    if "call_date" in data:
        doc.call_date = data.get("call_date")

    if "description" in data:
        doc.description = data.get("description")

    if "next_followup_date" in data:
        doc.next_followup_date = data.get("next_followup_date")

    if "call_duration" in data:
        doc.call_duration = data.get("call_duration")

    if "note" in data:
        doc.note = data.get("note")

    if "call_type" in data:
        doc.call_type = data.get("call_type")

    # Save changes
    doc.save()

    return {
        "success": True,
        "message": "Call log updated successfully",
        "data": doc.name
    }
import frappe

@frappe.whitelist()
def get_visitor_data():
    """
    Get the visitor data for the current user.
    """
    visitor = frappe.get_all("Visitor", fields=["name", "visitor_name", "visitor_intime", "visitor_outtime","visitor_purpose", "contact_number", "meeting_with", "id_card", "number_of_person", "attach_document", "note"])
    for v in visitor:
        print(v.attach_document)
        v.attach_document = frappe.utils.get_url()+v.attach_document if v.attach_document else None
    return {
        "success": True,
        "message": "Visitor data fetched successfully", 
        "data": visitor
    }

@frappe.whitelist()
def get_admission_enquiry():
    """
    Get the admission enquiry data.
    """
    enquiry = frappe.get_all("Admission Enquiry", fields=["name", "name1", "address", "enquiry_date", "reference", "no_of_children", "mobile_no", "description", "next_followup_date", "source", "email", "note","status","class"])
    return {
        "success": True,
        "message": "Admission enquiry data fetched successfully",
        "data": enquiry
    }

@frappe.whitelist(methods="POST")
def create_visitor():
    """
    Create a new visitor.
    smaple request:
    {
        "visitor_name": "John Doe",
        "visitor_intime": "2026-04-13 10:00:00",
        "visitor_outtime": "2026-04-13 11:00:00",
        "visitor_purpose": "Meeting",
        "contact_number": "1234567890",
        "meeting_with": "John Doe",
    }
    """
    data = frappe.request.get_json()
    print("json data", data)
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

@frappe.whitelist(methods="POST")
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
        "note": "I am interested in your school",
    }
    """
    data = frappe.request.get_json()
    print("json data", data)
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
    })
    enquiry.insert()
    return {
        "success": True,
        "message": "Admission enquiry created successfully",
        "data": enquiry.name1
    }
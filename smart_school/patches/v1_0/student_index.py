import frappe

def execute():
    # frappe.db.add_index("Student","enabled")
    # frappe.db.add_index("Student","user")
    # frappe.db.add_index("Student Guardian", ["parent", "relation"])
    indexes = [
        ("Student Guardian", ["parent", "relation"]),
        ("Student Guardian", ["guardian_name", "relation"]),
        ("Student", ["enabled", "name"]),
        ("Student", ["student_email_id", "enabled"]),
        ("Student",["user","name"]),
    ]

    for doctype, fields in indexes:
        try:
            if not frappe.db.has_index(doctype, fields):
                frappe.db.add_index(doctype, fields)
        except Exception:
            frappe.log_error(
                title="Index Creation Failed",
                message=f"{doctype} - {fields}"
            )
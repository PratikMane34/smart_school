import frappe

@frappe.whitelist()
def get_classes():
    return frappe.get_all(
        "Class",
        fields=["name", "class_name"],
        order_by="name"
    )

@frappe.whitelist()
def get_sections(class_name=None):
    filters = {}
    if class_name:
        filters["class"] = class_name
    return frappe.get_all(
        "Class Division",
        filters=filters,
        fields=["name", "division", "class"],
        order_by="division"
    )

@frappe.whitelist()
def get_academic_years():
    return frappe.get_all(
        "Academic Year",          # confirm doctype name in your app
        fields=["name"],
        order_by="name desc"
    )

@frappe.whitelist()
def get_teachers():
    return frappe.get_all(
        "HR Employee",
        filters={"designation": "Teacher"},   # adjust filter if needed
        fields=["name", "employee_name", "employee_id"],
        order_by="employee_name"
    )

@frappe.whitelist()
def get_subjects(class_name=None):
    filters = {}
    if class_name:
        filters["class"] = class_name
    return frappe.get_all(
        "Subject",
        filters=filters,
        fields=["name", "subject_name", "subject_code"],
        order_by="subject_name"
    )
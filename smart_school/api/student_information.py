import frappe

@frappe.whitelist()
def get_student_information():
    """
    Get the student information.
    """
    student = frappe.get_all("Student", filters={"enabled": 1}, fields=["name", "first_name", "last_name", "user","student_email_id", "student_mobile_number","date_of_birth","blood_group","gender","nationality","address_line_1","address_line_2","pincode","city","state","country"])
    student_parents = frappe.get_all("Student Guardian",filters={"relation":"Father"},fields=["guardian_name","parent"])
    return {
        "success": True,
        "message": "Student information fetched successfully",
        "data": student
    }
import frappe

@frappe.whitelist()
def get_student_details():
    """
    Get the student information along with guardian info.
    """
    students = frappe.get_all(
        "Student",
        filters={"enabled": 1},
        fields=[
            "name", "first_name", "last_name", "user",
            "student_email_id", "student_mobile_number",
            "date_of_birth", "blood_group", "gender",
            "nationality", "address_line_1", "address_line_2",
            "pincode", "city", "state", "country"
        ]
    )

    guardians = frappe.get_all(
        "Student Guardian",
        filters={"relation": "Father"},
        fields=["guardian_name", "parent"]
    )

    guardian_map = {}
    for g in guardians:
        guardian_map.setdefault(g.parent, []).append(g)

    for s in students:
        s["guardians"] = guardian_map.get(s.name, [])

    return {
        "success": True,
        "message": "Student information fetched successfully",
        "data": students
    }

@frappe.whitelist()
def get_student_profile(name=None):
    if not name:
        frappe.throw("Student ID (name) is required")
    
    student_data = frappe.get_all("Student",filters= {"name":name},fields = ["blood_group","date_of_birth","gender","name","image","joining_date","student_email_id","student_mobile_number","student_name","student_category"])

    return {
        "success" : True,
        "data" : student_data
    }
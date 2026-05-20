import frappe

# Student Attendance APIs -----------------------------------
@frappe.whitelist()
def get_attendance(student_group=None, attendance_date=None, batch=None, start_page=1, page_size=50):
    if not student_group:
        frappe.throw("Student Group is required")

    attendance_records = frappe.get_all(
        "Student Attendance",
        filters={"student_group": student_group, "date": attendance_date},
        fields=["name", "student", "student_name", "student_group", "date", "status"],
        start=(int(start_page) - 1) * int(page_size),
        page_length=int(page_size)
    )

    return {
        "success": True,
        "message": "Attendance records fetched successfully",
        "data": attendance_records
    }

@frappe.whitelist()
def get_student_list_by_group(student_group=None, batch=None, start_page=1, page_size=50):
    if not student_group:
        frappe.throw("Student Group is required")
    if not batch:
        frappe.throw("Batch is required")

    students = frappe.get_all(
        "Student Group Student",
        filters={"parent": student_group, "active": 1, "batch": batch},
        fields=["name", "student_name", "group_roll_number"],
        start=(int(start_page) - 1) * int(page_size),
        page_length=int(page_size)
    )

    return {
        "success": True,
        "message": "Students fetched successfully",
        "data": students
    }

@frappe.whitelist()
def save_attendance(attendance_data):
    if not attendance_data:
        frappe.throw("Attendance data is required")

    for record in attendance_data:
        attendance_doc = frappe.get_doc({
            "doctype": "Student Attendance",
            "student": record.get("name"),
            "student_name": record.get("student_name"),
            "student_group": record.get("student_group"),
            # "batch": record.get("batch"),
            "date": record.get("date"),
            "status": record.get("status")
        })
        attendance_doc.insert()

    return {
        "success": True,
        "message": "Attendance records saved successfully"
    }

# ----- Student Leave Application APIs -----------------------------------
@frappe.whitelist()
def get_leave_applications(student_group=None, batch=None, start_page=1, page_size=50):
    if not student_group:
        frappe.throw("Student Group is required")
    if not batch:
        frappe.throw("Batch is required")

    leave_applications = frappe.get_all(
        "Student Leave Application",
        filters={"student_group": student_group},
        fields=["name", "student", "student_name", "from_date", "to_date"],
        start=(int(start_page) - 1) * int(page_size),
        page_length=int(page_size)
    )

    return {
        "success": True,
        "message": "Leave applications fetched successfully",
        "data": leave_applications
    }

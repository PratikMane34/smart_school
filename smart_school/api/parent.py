import frappe
from smart_school.api._guards import assert_parent_of
from smart_school.api.auth import _get_children_for_guardian


# ─────────────────────────────────────────────
# Children & profile
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_children():
    """List students that the current user is a guardian of."""
    user = frappe.session.user
    children = _get_children_for_guardian(user)
    return {
        "success": True,
        "message": "Children fetched successfully",
        "data": children
    }


@frappe.whitelist()
def get_child_profile(student=None):
    """Profile of a single student. Caller must be a guardian of <student>."""
    if not student:
        frappe.throw("student is required")
    assert_parent_of(student)

    profile = frappe.get_doc("Student", student).as_dict()
    return {
        "success": True,
        "message": "Student profile fetched successfully",
        "data": profile
    }


# ─────────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_attendance(student=None, from_date=None, to_date=None,
                   start_page=1, page_size=50):
    """
    Attendance history of one of the parent's children.

    Query params: student (required), from_date, to_date, start_page, page_size
    """
    if not student:
        frappe.throw("student is required")
    assert_parent_of(student)

    filters = {"student": student}
    if from_date and to_date:
        filters["date"] = ["between", [from_date, to_date]]
    elif from_date:
        filters["date"] = [">=", from_date]
    elif to_date:
        filters["date"] = ["<=", to_date]

    start_page = int(start_page)
    page_size = int(page_size)

    records = frappe.get_all(
        "Student Attendance",
        filters=filters,
        fields=["name", "student", "student_name", "student_group", "date", "status"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="date desc"
    )

    summary = frappe.db.sql(
        """
        SELECT status, COUNT(*) AS count
        FROM `tabStudent Attendance`
        WHERE student = %(student)s
          AND date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY status
        """,
        {
            "student": student,
            "from_date": from_date or "1900-01-01",
            "to_date": to_date or "2999-12-31",
        },
        as_dict=True
    )

    return {
        "success": True,
        "message": "Attendance fetched successfully",
        "data": records,
        "summary": summary,
        "total": frappe.db.count("Student Attendance", filters=filters),
        "start_page": start_page,
        "page_size": page_size
    }


# ─────────────────────────────────────────────
# Timetable
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_timetable(student=None, day=None):
    """
    Timetable for a child's class/division based on their current Program
    Enrollment. Caller must be guardian of <student>.
    """
    if not student:
        frappe.throw("student is required")
    assert_parent_of(student)

    enrollment = frappe.db.get_value(
        "Program Enrollment",
        {"student": student},
        ["program", "academic_year", "student_batch_name"],
        as_dict=True,
        order_by="academic_year desc"
    )

    if not enrollment:
        return {
            "success": True,
            "message": "No active enrollment found for this student",
            "data": []
        }

    # Smart School's Timetable doctype keys off class/division/academic_year,
    # where class and division are the school's own concepts.  We expose what
    # we have: a list of slots filtered by academic_year + division (if mapped).
    timetables = frappe.get_all(
        "Timetable",
        filters={
            "academic_year": enrollment.academic_year,
            "docstatus": 1,
        },
        fields=["name", "class", "division", "academic_year"]
    )

    if not timetables:
        return {
            "success": True,
            "message": "No active timetable found",
            "data": []
        }

    slot_filters = {"parent": ["in", [t.name for t in timetables]]}
    if day:
        slot_filters["day"] = day

    slots = frappe.get_all(
        "Timetable Slot",
        filters=slot_filters,
        fields=["parent", "day", "period", "start_time", "end_time",
                "subject", "teacher", "room"],
        order_by="day, start_time"
    )

    return {
        "success": True,
        "message": "Timetable fetched successfully",
        "data": slots
    }


# ─────────────────────────────────────────────
# Fees
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_fees(student=None, outstanding_only=0, start_page=1, page_size=20):
    """Fee invoices for a child."""
    if not student:
        frappe.throw("student is required")
    assert_parent_of(student)

    filters = {"student": student}
    if int(outstanding_only or 0):
        filters["outstanding_amount"] = [">", 0]
        filters["docstatus"] = ["!=", 2]

    start_page = int(start_page)
    page_size = int(page_size)

    fees = frappe.get_all(
        "Fees",
        filters=filters,
        fields=["name", "student", "student_name", "program", "academic_year",
                "academic_term", "fee_structure", "fee_schedule",
                "posting_date", "due_date", "grand_total", "outstanding_amount",
                "docstatus"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="due_date desc"
    )

    return {
        "success": True,
        "message": "Fees fetched successfully",
        "data": fees,
        "total": frappe.db.count("Fees", filters=filters)
    }


# ─────────────────────────────────────────────
# Calendar & announcements (audience-aware)
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_calendar(from_date=None, to_date=None):
    """School events visible to the parent (audience: All or matching one of
    their children's classes)."""
    user = frappe.session.user
    children = _get_children_for_guardian(user)

    classes = list({c.get("program") for c in children if c.get("program")})

    filters = []
    if from_date:
        filters.append(["start_date", ">=", from_date])
    if to_date:
        filters.append(["start_date", "<=", to_date])

    or_filters = [["audience", "=", "All"], ["audience", "=", "Role"]]
    if classes:
        or_filters.append(["class", "in", classes])

    events = frappe.get_all(
        "School Event",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "title", "event_type", "start_date", "end_date",
                "all_day", "audience", "class", "description", "attachment"],
        order_by="start_date asc"
    )

    for e in events:
        if e.get("attachment"):
            e["attachment"] = frappe.utils.get_url() + e["attachment"]

    return {
        "success": True,
        "message": "Calendar fetched successfully",
        "data": events
    }


@frappe.whitelist()
def get_announcements(start_page=1, page_size=20):
    """Active announcements addressed to All or to the Parent role."""
    today = frappe.utils.nowdate()

    start_page = int(start_page)
    page_size = int(page_size)

    announcements = frappe.get_all(
        "Announcement",
        filters=[["valid_from", "<=", today]],
        or_filters=[
            ["audience", "=", "All"],
            ["audience", "=", "Role"],
        ],
        fields=["name", "title", "body", "audience", "class", "role",
                "valid_from", "valid_to", "attachment", "posted_by", "creation"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="creation desc"
    )

    # Drop expired announcements
    visible = []
    for a in announcements:
        if a.valid_to and a.valid_to < today:
            continue
        if a.audience == "Role" and a.role != "Parent":
            continue
        if a.get("attachment"):
            a["attachment"] = frappe.utils.get_url() + a["attachment"]
        visible.append(a)

    return {
        "success": True,
        "message": "Announcements fetched successfully",
        "data": visible
    }

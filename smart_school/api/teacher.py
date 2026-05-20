import frappe
from smart_school.api._guards import assert_teacher_of_group, require_role
from smart_school.api.auth import _get_teacher_context


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _current_employee():
    """Return the HR Employee linked to the current user, or throw."""
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": frappe.session.user},
        "name"
    )
    if not employee:
        frappe.throw("You are not linked to any Employee record.", frappe.PermissionError)
    return employee


def _current_instructors(employee):
    """Return the Instructor doc names tied to <employee>."""
    return frappe.get_all(
        "Instructor",
        filters={"employee": employee},
        pluck="name"
    )


# ─────────────────────────────────────────────
# Today / overview
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_today():
    """Today's overview for the logged-in teacher: timetable slots for today,
    number of student groups, and the underlying employee context."""
    context = _get_teacher_context(frappe.session.user)
    if not context:
        return {
            "success": True,
            "message": "No teacher context for this user",
            "data": None
        }

    today_day = frappe.utils.getdate(frappe.utils.nowdate()).strftime("%A")
    employee = context["employee"]

    slots = frappe.db.sql(
        """
        SELECT ts.day, ts.period, ts.start_time, ts.end_time,
               ts.subject, ts.room, tt.`class`, tt.division
        FROM `tabTimetable Slot` ts
        JOIN `tabTimetable` tt ON tt.name = ts.parent
        WHERE ts.teacher = %(employee)s
          AND ts.day = %(day)s
          AND tt.docstatus = 1
        ORDER BY ts.start_time
        """,
        {"employee": employee, "day": today_day},
        as_dict=True
    )

    instructor_names = _current_instructors(employee)
    group_count = 0
    if instructor_names:
        group_count = frappe.db.count(
            "Student Group Instructor",
            filters={"instructor": ["in", instructor_names]}
        )

    return {
        "success": True,
        "message": "Today fetched successfully",
        "data": {
            "context": context,
            "day": today_day,
            "slots": slots,
            "group_count": group_count,
        }
    }


# ─────────────────────────────────────────────
# My student groups
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_my_groups(academic_year=None):
    """List Student Groups where the current teacher is an instructor."""
    employee = _current_employee()
    instructor_names = _current_instructors(employee)
    if not instructor_names:
        return {
            "success": True,
            "message": "No instructor records found",
            "data": []
        }

    rows = frappe.get_all(
        "Student Group Instructor",
        filters={"instructor": ["in", instructor_names]},
        fields=["parent"]
    )
    group_names = list({r.parent for r in rows})
    if not group_names:
        return {
            "success": True,
            "message": "No student groups assigned",
            "data": []
        }

    group_filters = {"name": ["in", group_names]}
    if academic_year:
        group_filters["academic_year"] = academic_year

    groups = frappe.get_all(
        "Student Group",
        filters=group_filters,
        fields=["name", "student_group_name", "program", "course",
                "academic_year", "academic_term", "batch"]
    )

    return {
        "success": True,
        "message": "Student groups fetched successfully",
        "data": groups
    }


# ─────────────────────────────────────────────
# Attendance
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_students_in_group(student_group=None, batch=None):
    """List students of a group the teacher owns."""
    if not student_group:
        frappe.throw("student_group is required")
    assert_teacher_of_group(student_group)

    filters = {"parent": student_group, "active": 1}
    if batch:
        filters["batch"] = batch

    students = frappe.get_all(
        "Student Group Student",
        filters=filters,
        fields=["name", "student", "student_name", "group_roll_number"]
    )

    return {
        "success": True,
        "message": "Students fetched successfully",
        "data": students
    }


@frappe.whitelist(methods=["POST"])
def take_attendance():
    """
    Mark attendance for a class.

    POST /api/method/smart_school.api.teacher.take_attendance
    Body: {
        "student_group": "STG-...",
        "date": "2026-05-20",
        "records": [
            { "student": "EDU-STU-0001", "student_name": "Aarav", "status": "Present" },
            { "student": "EDU-STU-0002", "student_name": "Anaya", "status": "Absent" }
        ]
    }
    """
    require_role("Teacher", "School Admin")

    data = frappe.request.get_json() or {}
    student_group = data.get("student_group")
    date = data.get("date") or frappe.utils.nowdate()
    records = data.get("records") or []

    if not student_group or not records:
        frappe.throw("student_group and records are required")

    assert_teacher_of_group(student_group)

    created = []
    skipped = []

    for r in records:
        student = r.get("student") or r.get("name")
        status = r.get("status")
        if not student or not status:
            skipped.append({"student": student, "reason": "missing student or status"})
            continue

        existing = frappe.db.exists("Student Attendance", {
            "student": student,
            "student_group": student_group,
            "date": date,
            "docstatus": ["!=", 2],
        })
        if existing:
            skipped.append({"student": student, "reason": "already marked"})
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Student Attendance",
                "student": student,
                "student_name": r.get("student_name"),
                "student_group": student_group,
                "date": date,
                "status": status,
            })
            doc.insert()
            created.append(doc.name)
        except Exception as e:
            skipped.append({"student": student, "reason": str(e)})

    frappe.db.commit()

    return {
        "success": True,
        "message": f"Marked {len(created)} attendance records ({len(skipped)} skipped)",
        "data": {
            "created": created,
            "skipped": skipped,
        }
    }


# ─────────────────────────────────────────────
# My timetable
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_my_timetable(academic_year=None, day=None):
    """Teacher's own timetable across all classes/divisions for an academic year."""
    employee = _current_employee()

    params = {"teacher": employee}
    day_clause = ""
    year_clause = ""

    if academic_year:
        year_clause = "AND tt.academic_year = %(academic_year)s"
        params["academic_year"] = academic_year
    if day:
        day_clause = "AND ts.day = %(day)s"
        params["day"] = day

    slots = frappe.db.sql(
        """
        SELECT ts.day, ts.period, ts.start_time, ts.end_time,
               ts.subject, ts.room, tt.`class`, tt.division, tt.academic_year
        FROM `tabTimetable Slot` ts
        JOIN `tabTimetable` tt ON tt.name = ts.parent
        WHERE ts.teacher = %(teacher)s
          AND tt.docstatus = 1
          """ + year_clause + """
          """ + day_clause + """
        ORDER BY ts.day, ts.start_time
        """,
        params,
        as_dict=True
    )

    return {
        "success": True,
        "message": "Timetable fetched successfully",
        "data": slots
    }


# ─────────────────────────────────────────────
# Announcements
# ─────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def post_announcement():
    """
    Teacher posts an announcement. Defaults to audience='Student Group'
    targeting one of the teacher's groups when student_group is provided.
    """
    require_role("Teacher", "School Admin")

    data = frappe.request.get_json() or {}

    if not (data.get("title") and data.get("body")):
        frappe.throw("title and body are required")

    audience = data.get("audience") or ("Student Group" if data.get("student_group") else "Role")
    student_group = data.get("student_group")

    if audience == "Student Group":
        if not student_group:
            frappe.throw("student_group is required when audience is 'Student Group'")
        assert_teacher_of_group(student_group)

    ann = frappe.get_doc({
        "doctype": "Announcement",
        "title": data.get("title"),
        "body": data.get("body"),
        "audience": audience,
        "class": data.get("class"),
        "role": data.get("role") or ("Parent" if audience == "Role" else None),
        "student_group": student_group,
        "valid_from": data.get("valid_from") or frappe.utils.nowdate(),
        "valid_to": data.get("valid_to"),
        "attachment": data.get("attachment"),
        "posted_by": frappe.session.user,
    })
    ann.insert()

    return {
        "success": True,
        "message": "Announcement posted successfully",
        "data": ann.name
    }


@frappe.whitelist()
def get_announcements(start_page=1, page_size=20):
    """List announcements relevant to the teacher (all + role=Teacher + their
    own student groups)."""
    employee = _current_employee()
    instructor_names = _current_instructors(employee)

    group_names = []
    if instructor_names:
        rows = frappe.get_all(
            "Student Group Instructor",
            filters={"instructor": ["in", instructor_names]},
            fields=["parent"]
        )
        group_names = list({r.parent for r in rows})

    today = frappe.utils.nowdate()
    start_page = int(start_page)
    page_size = int(page_size)

    or_filters = [
        ["audience", "=", "All"],
        ["audience", "=", "Role"],
    ]
    if group_names:
        or_filters.append(["student_group", "in", group_names])

    announcements = frappe.get_all(
        "Announcement",
        filters=[["valid_from", "<=", today]],
        or_filters=or_filters,
        fields=["name", "title", "body", "audience", "class", "role",
                "student_group", "valid_from", "valid_to", "attachment",
                "posted_by", "creation"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="creation desc"
    )

    visible = []
    for a in announcements:
        if a.valid_to and a.valid_to < today:
            continue
        if a.audience == "Role" and a.role not in (None, "", "Teacher"):
            continue
        if a.get("attachment"):
            a["attachment"] = frappe.utils.get_url() + a["attachment"]
        visible.append(a)

    return {
        "success": True,
        "message": "Announcements fetched successfully",
        "data": visible
    }

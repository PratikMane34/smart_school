import frappe

@frappe.whitelist()
def get_timetable(class_name, division, academic_year, day=None):
    """Fetch active timetable slots for a class/division."""
    tt = frappe.db.get_value(
        "Timetable",
        {"class": class_name, "division": division,
         "academic_year": academic_year, "docstatus": 1},
        "name"
    )
    if not tt:
        frappe.throw("No submitted timetable found")

    filters = {"parent": tt}
    if day:
        filters["day"] = day

    slots = frappe.get_all(
        "Timetable Slot",
        filters=filters,
        fields=["day", "period", "start_time", "end_time",
                "subject", "teacher", "room"],
        order_by="day, start_time"
    )
    return slots


@frappe.whitelist()
def get_teacher_schedule(teacher, academic_year, day=None):
    """All slots for teacher across classes."""
    filters = {"teacher": teacher}
    if day:
        filters["day"] = day

    slots = frappe.db.sql("""
        SELECT ts.day, ts.period, ts.start_time, ts.end_time,
               ts.subject, ts.room, tt.class, tt.division
        FROM `tabTimetable Slot` ts
        JOIN `tabTimetable` tt ON tt.name = ts.parent
        WHERE ts.teacher = %(teacher)s
          AND tt.academic_year = %(academic_year)s
          AND tt.docstatus = 1
          {day_filter}
        ORDER BY ts.day, ts.start_time
    """.format(day_filter="AND ts.day = %(day)s" if day else ""),
    {"teacher": teacher, "academic_year": academic_year, "day": day},
    as_dict=True)
    return slots
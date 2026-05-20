from .workspace import get_workspace_data, get_sidebar
from .auth import login, validate_token, logout, forgot_password, reset_password
from .front_office import (
    get_visitor_data, create_visitor,
    get_admission_enquiry, create_admission_enquiry,
    update_admission_enquiry, delete_admission_enquiry,
    convert_enquiry_to_applicant,
)
from .student_information import get_student_details, get_student_profile
from .enquiry_call_log import (
    get_enquiry_call_log, call_logs, update_call_log,
    send_followup_reminders,
)
from .attendance import (
    get_attendance, get_student_list_by_group, save_attendance,
    get_leave_applications,
)
from .timetable import get_timetable, get_teacher_schedule
from .fees import (
    get_fee_structures, get_fee_schedules, get_fees,
    get_outstanding_by_program, generate_fees_for_group,
)
from .calendar import (
    get_events, get_event, create_event, update_event, delete_event,
)
from .messaging import (
    get_announcements, get_announcement, create_announcement,
    update_announcement, delete_announcement,
)
from . import parent, teacher  # noqa: F401  (loaded so frappe.whitelist finds them)

__all__ = [
    # auth
    "login", "logout", "validate_token", "forgot_password", "reset_password",
    # workspace / nav
    "get_workspace_data", "get_sidebar",
    # front office
    "get_visitor_data", "create_visitor",
    "get_admission_enquiry", "create_admission_enquiry",
    "update_admission_enquiry", "delete_admission_enquiry",
    "convert_enquiry_to_applicant",
    # call logs
    "get_enquiry_call_log", "call_logs", "update_call_log",
    "send_followup_reminders",
    # student info
    "get_student_details", "get_student_profile",
    # attendance
    "get_attendance", "get_student_list_by_group", "save_attendance",
    "get_leave_applications",
    # timetable
    "get_timetable", "get_teacher_schedule",
    # fees
    "get_fee_structures", "get_fee_schedules", "get_fees",
    "get_outstanding_by_program", "generate_fees_for_group",
    # calendar
    "get_events", "get_event", "create_event", "update_event", "delete_event",
    # messaging
    "get_announcements", "get_announcement", "create_announcement",
    "update_announcement", "delete_announcement",
]

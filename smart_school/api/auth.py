# smart_school/api/auth.py

import frappe
from frappe import _
from smart_school.utils.rate_limiter import rate_limit


# ─────────────────────────────────────────────
# LOGIN - Returns Bearer Token
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@rate_limit(max_requests=20, window=60)
def login(usr=None, pwd=None):
    """
    Login endpoint that returns a Bearer token.

    POST /api/method/smart_school.api.auth.login
    Body: { "usr": "user@example.com", "pwd": "password" }

    Response:
    {
        "success": true,
        "message": "Login successful",
        "data": {
            "token": "Bearer <api_key>:<api_secret>",
            "user": "user@example.com",
            "full_name": "John Doe",
            "user_type": "System User",
            "roles": ["Parent"],
            "parent_of": [ ... ],   # only when user has Parent role
            "teacher": { ... }       # only when user has Teacher role
        }
    }
    """
    try:
        if not usr or not pwd:
            frappe.throw(
                _("Please provide both username and password."),
                frappe.AuthenticationError
            )

        frappe.local.login_manager.authenticate(usr, pwd)
        frappe.local.login_manager.post_login()

        user = frappe.local.session_obj.user

        api_key = frappe.db.get_value("User", user, "api_key")
        api_secret = _get_or_generate_api_secret(user, api_key)

        if not api_key:
            api_key = frappe.generate_hash(length=15)
            frappe.db.set_value("User", user, "api_key", api_key)
            api_secret = _generate_api_secret(user)

        token = f"{api_key}:{api_secret}"

        user_doc = frappe.get_doc("User", user)
        roles = [r.role for r in user_doc.roles]

        data = {
            "token": f"Bearer {token}",
            "user": user,
            "full_name": user_doc.full_name,
            "user_type": user_doc.user_type,
            "roles": roles,
        }

        if "Parent" in roles:
            data["parent_of"] = _get_children_for_guardian(user)
        if "Teacher" in roles:
            data["teacher"] = _get_teacher_context(user)

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("Login successful"),
            "data": data
        }

    except frappe.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["http_status_code"] = 401
        return {
            "success": False,
            "message": _("Invalid username or password.")
        }
    except Exception as e:
        frappe.log_error(f"Login error: {str(e)}", "Auth API")
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "message": _("An error occurred during login.")
        }


# ─────────────────────────────────────────────
# LOGOUT - Requires Bearer Token
# ─────────────────────────────────────────────

@frappe.whitelist()
@rate_limit(max_requests=20, window=60)
def logout():
    """
    Logout endpoint - clears the current server session.

    The API token is intentionally NOT rotated here; rotating it would
    invalidate every other device that the same user is signed in on.
    Mobile clients should simply discard their stored token on logout.

    POST /api/method/smart_school.api.auth.logout
    Headers: { "Authorization": "Bearer <api_key>:<api_secret>" }

    Response:
    {
        "success": true,
        "message": "Logged out successfully"
    }
    """
    try:
        user = frappe.session.user

        if user == "Guest":
            frappe.local.response["http_status_code"] = 401
            return {
                "success": False,
                "message": _("Not authenticated.")
            }

        frappe.local.login_manager.logout()

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("Logged out successfully.")
        }

    except Exception as e:
        frappe.log_error(f"Logout error: {str(e)}", "Auth API")
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "message": _("An error occurred during logout.")
        }


# ─────────────────────────────────────────────
# FORGOT PASSWORD - Guest Accessible
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@rate_limit(max_requests=20, window=60)
def forgot_password(email=None):
    """
    Forgot password endpoint - sends password reset email.
    
    POST /api/method/smart_school.api.auth.forgot_password
    Body: { "email": "user@example.com" }
    
    Response:
    {
        "success": true,
        "message": "Password reset instructions have been sent to your email."
    }
    """
    try:
        if not email:
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "message": _("Please provide an email address.")
            }

        # Validate email format
        if not frappe.utils.validate_email_address(email):
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "message": _("Please provide a valid email address.")
            }

        # Check if user exists (but don't reveal this to the client for security)
        if not frappe.db.exists("User", email):
            # Return same success message to prevent user enumeration
            frappe.local.response["http_status_code"] = 200
            return {
                "success": True,
                "message": _("If an account with that email exists, password reset instructions have been sent.")
            }

        # Generate reset key and send email
        user = frappe.get_doc("User", email)

        if not user.enabled:
            frappe.local.response["http_status_code"] = 200
            return {
                "success": True,
                "message": _("If an account with that email exists, password reset instructions have been sent.")
            }

        # Use Frappe's built-in reset password method
        frappe.sendmail(
            recipients=email,
            subject=_("Password Reset"),
            template="password_reset",
            args={
                "link": _get_password_reset_link(user)
            },
            header=[_("Password Reset Request"), "green"]
        )

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("If an account with that email exists, password reset instructions have been sent.")
        }

    except Exception as e:
        frappe.log_error(f"Forgot password error: {str(e)}", "Auth API")
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "message": _("An error occurred. Please try again later.")
        }


# ─────────────────────────────────────────────
# RESET PASSWORD - Guest Accessible
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@rate_limit(max_requests=20, window=60)
def reset_password(key=None, new_password=None):
    """
    Reset password using the reset key from email.
    
    POST /api/method/smart_school.api.auth.reset_password
    Body: { "key": "<reset_key>", "new_password": "newpass123" }
    """
    try:
        if not key or not new_password:
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "message": _("Please provide both reset key and new password.")
            }

        # Validate password strength
        _validate_password_strength(new_password)

        # Find user with this reset key
        user = frappe.db.get_value(
            "User",
            {"reset_password_key": key},
            ["name", "reset_password_key"],
            as_dict=True
        )

        if not user:
            frappe.local.response["http_status_code"] = 400
            return {
                "success": False,
                "message": _("Invalid or expired reset link.")
            }

        # Update the password
        frappe.db.set_value("User", user.name, "reset_password_key", "")
        update_password(user.name, new_password)
        frappe.db.commit()

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("Password has been reset successfully. You can now log in.")
        }

    except frappe.ValidationError as e:
        frappe.local.response["http_status_code"] = 400
        return {
            "success": False,
            "message": str(e)
        }
    except Exception as e:
        frappe.log_error(f"Reset password error: {str(e)}", "Auth API")
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "message": _("An error occurred. Please try again later.")
        }


# ─────────────────────────────────────────────
# VALIDATE TOKEN - Check if token is still valid
# ─────────────────────────────────────────────

@frappe.whitelist()
@rate_limit(max_requests=20, window=60)
def validate_token():
    """
    Validate the current Bearer token and return the same context payload
    as login. Clients call this on app start (with a stored token) to
    rehydrate user context without re-prompting for password.

    GET /api/method/smart_school.api.auth.validate_token
    Headers: { "Authorization": "Bearer <api_key>:<api_secret>" }
    """
    try:
        user = frappe.session.user

        if user == "Guest":
            frappe.local.response["http_status_code"] = 401
            return {
                "success": False,
                "message": _("Invalid or expired token.")
            }

        user_doc = frappe.get_doc("User", user)
        roles = [r.role for r in user_doc.roles]

        data = {
            "user": user,
            "full_name": user_doc.full_name,
            "user_type": user_doc.user_type,
            "roles": roles,
        }

        if "Parent" in roles:
            data["parent_of"] = _get_children_for_guardian(user)
        if "Teacher" in roles:
            data["teacher"] = _get_teacher_context(user)

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("Token is valid."),
            "data": data
        }

    except Exception as e:
        frappe.log_error(f"Validate token error: {str(e)}", "Auth API")
        frappe.local.response["http_status_code"] = 500
        return {
            "success": False,
            "message": _("An error occurred during token validation.")
        }


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

def _generate_api_secret(user):
    """Generate a new API secret for the user."""
    api_secret = frappe.generate_hash(length=15)
    frappe.db.set_value("User", user, "api_secret", api_secret)
    frappe.db.commit()
    return api_secret


def _get_or_generate_api_secret(user, api_key):
    """Get existing API secret or generate a new one."""
    if not api_key:
        return None

    api_secret = frappe.utils.password.get_decrypted_password(
        "User", user, fieldname="api_secret"
    )

    if not api_secret:
        api_secret = _generate_api_secret(user)

    return api_secret


def _get_password_reset_link(user_doc):
    """Generate password reset link."""
    key = frappe.generate_hash(length=32)
    user_doc.db_set("reset_password_key", key)
    frappe.db.commit()

    url = frappe.utils.get_url(f"/update-password?key={key}")
    return url


def _validate_password_strength(password):
    """Validate password meets minimum requirements."""
    if len(password) < 8:
        frappe.throw(_("Password must be at least 8 characters long."))

    # Use Frappe's built-in password policy if available
    from frappe.utils.password import test_password_strength
    result = test_password_strength(password)

    if result.get("feedback", {}).get("warning"):
        frappe.throw(result["feedback"]["warning"])


def update_password(user, new_password):
    """Update user password."""
    from frappe.utils.password import update_password as _update_password
    _update_password(user, new_password)


# ─────────────────────────────────────────────
# CONTEXT HELPERS (Parent / Teacher)
# ─────────────────────────────────────────────

def _get_children_for_guardian(user):
    """
    Return the list of students that the given user is a guardian of.

    Resolution:
        Guardian (where user = <user> OR email_address = <user>)
        -> Student Guardian rows (where guardian = guardian.name)
        -> Student (the row's parent)
    """
    if not user or user == "Guest":
        return []

    guardians = frappe.get_all(
        "Guardian",
        filters={"user": user},
        fields=["name"]
    )

    if not guardians:
        guardians = frappe.get_all(
            "Guardian",
            filters={"email_address": user},
            fields=["name"]
        )

    if not guardians:
        return []

    guardian_names = [g.name for g in guardians]

    student_guardian_rows = frappe.get_all(
        "Student Guardian",
        filters={"guardian": ["in", guardian_names]},
        fields=["parent", "guardian", "relation"]
    )

    student_ids = list({row.parent for row in student_guardian_rows if row.parent})
    if not student_ids:
        return []

    students = frappe.get_all(
        "Student",
        filters={"name": ["in", student_ids]},
        fields=["name", "student_name", "image", "student_email_id"]
    )

    enrollments = frappe.get_all(
        "Program Enrollment",
        filters={"student": ["in", student_ids]},
        fields=["student", "program", "academic_year", "student_batch_name", "student_category"],
        order_by="academic_year desc"
    )

    enrollment_by_student = {}
    for e in enrollments:
        enrollment_by_student.setdefault(e.student, e)

    children = []
    for s in students:
        enrollment = enrollment_by_student.get(s.name)
        children.append({
            "student": s.name,
            "student_name": s.student_name,
            "student_email_id": s.student_email_id,
            "image": s.image,
            "program": enrollment.program if enrollment else None,
            "academic_year": enrollment.academic_year if enrollment else None,
            "student_batch_name": enrollment.student_batch_name if enrollment else None,
        })

    return children


def _get_teacher_context(user):
    """
    Return the HR Employee context for a teacher user, plus a count of
    timetable slots scheduled for today.

    Resolution:
        HR Employee (where user_id = <user>)
        + count Timetable Slot rows for that employee on today's weekday
          across submitted Timetables.
    """
    if not user or user == "Guest":
        return None

    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "employee_name", "designation"],
        as_dict=True
    )

    if not employee:
        return None

    today_day = frappe.utils.getdate(frappe.utils.nowdate()).strftime("%A")

    today_class_count = frappe.db.sql("""
        SELECT COUNT(*)
        FROM `tabTimetable Slot` ts
        JOIN `tabTimetable` tt ON tt.name = ts.parent
        WHERE ts.teacher = %(employee)s
          AND ts.day = %(day)s
          AND tt.docstatus = 1
    """, {"employee": employee.name, "day": today_day})[0][0]

    return {
        "employee": employee.name,
        "employee_name": employee.employee_name,
        "designation": employee.designation,
        "today_class_count": int(today_class_count or 0),
    }
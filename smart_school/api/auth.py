# your_app/api/auth.py

import frappe
from frappe import _
import json
import secrets
import hashlib
from smart_school.utils.rate_limiter import rate_limit


# ─────────────────────────────────────────────
# LOGIN - Returns Bearer Token
# ─────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
@rate_limit(max_requests=20, window=60)
def login(usr=None, pwd=None):
    """
    Login endpoint that returns a Bearer token.
    
    POST /api/method/your_app.api.auth.login
    Body: { "usr": "user@example.com", "pwd": "password" }
    
    Response:
    {
        "success": true,
        "message": "Login successful",
        "data": {
            "token": "Bearer <api_key>:<api_secret>",
            "user": "user@example.com",
            "full_name": "John Doe"
        }
    }
    """
    try:
        if not usr or not pwd:
            frappe.throw(
                _("Please provide both username and password."),
                frappe.AuthenticationError
            )

        # Authenticate user using Frappe's built-in method
        frappe.local.login_manager.authenticate(usr, pwd)
        frappe.local.login_manager.post_login()

        user = frappe.local.session_obj.user

        # Generate API keys if they don't exist
        api_key = frappe.db.get_value("User", user, "api_key")
        api_secret = _get_or_generate_api_secret(user, api_key)

        if not api_key:
            api_key = frappe.generate_hash(length=15)
            frappe.db.set_value("User", user, "api_key", api_key)
            api_secret = _generate_api_secret(user)

        token = f"{api_key}:{api_secret}"

        # Get user details
        user_doc = frappe.get_doc("User", user)

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("Login successful"),
            "data": {
                "token": f"Bearer {token}",
                "api_key": api_key,
                "api_secret": api_secret,
                "user": user,
                "full_name": user_doc.full_name,
                "user_type": user_doc.user_type,
                "roles": [r.role for r in user_doc.roles]
            }
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
    Logout endpoint - invalidates the API secret/token.
    
    POST /api/method/your_app.api.auth.logout
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

        # Regenerate API secret to invalidate the old token
        _generate_api_secret(user)

        # Clear session
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
    
    POST /api/method/your_app.api.auth.forgot_password
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
    
    POST /api/method/your_app.api.auth.reset_password
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
    Validate if the current Bearer token is still valid.
    
    GET /api/method/your_app.api.auth.validate_token
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

        frappe.local.response["http_status_code"] = 200
        return {
            "success": True,
            "message": _("Token is valid."),
            "data": {
                "user": user,
                "full_name": user_doc.full_name,
                "user_type": user_doc.user_type,
                "roles": [r.role for r in user_doc.roles]
            }
        }

    except Exception as e:
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
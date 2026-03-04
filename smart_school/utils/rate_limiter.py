# your_app/utils/rate_limiter.py

import frappe
import time
from functools import wraps


class RateLimitExceeded(Exception):
    pass


def rate_limit(max_requests=20, window=60):
    """
    Decorator to rate limit API endpoints.
    
    Args:
        max_requests: Maximum number of requests allowed in the window (default: 20)
        window: Time window in seconds (default: 60 seconds)
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Identify client by IP address or user
            client_ip = frappe.request.environ.get(
                "HTTP_X_FORWARDED_FOR",
                frappe.request.environ.get("REMOTE_ADDR", "unknown")
            )
            # Take first IP if multiple (proxy chain)
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()

            endpoint = fn.__name__
            cache_key = f"rate_limit:{endpoint}:{client_ip}"

            # Get current request log from cache
            request_log = frappe.cache().get_value(cache_key)

            now = time.time()

            if request_log is None:
                request_log = []

            # Filter out requests outside the current window
            request_log = [
                timestamp for timestamp in request_log
                if now - timestamp < window
            ]

            if len(request_log) >= max_requests:
                retry_after = int(window - (now - request_log[0]))
                frappe.local.response["http_status_code"] = 429
                frappe.local.response["headers"] = {
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(request_log[0] + window))
                }
                frappe.throw(
                    msg=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    title="Too Many Requests",
                    exc=frappe.TooManyRequestsError
                )

            # Log this request
            request_log.append(now)
            frappe.cache().set_value(cache_key, request_log, expires_in_sec=window)

            # Set rate limit headers on successful requests
            remaining = max_requests - len(request_log)
            frappe.local.response.setdefault("headers", {})
            frappe.local.response["headers"].update({
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(request_log[0] + window))
            })

            return fn(*args, **kwargs)
        return wrapper
    return decorator
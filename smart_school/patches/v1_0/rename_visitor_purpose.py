import frappe


def execute():
    """Rename the 'VIsitor Purpose' doctype (capital I typo) to 'Visitor Purpose'.

    Safe to run repeatedly: it is a no-op if the old name no longer exists.
    """
    old_name = "VIsitor Purpose"
    new_name = "Visitor Purpose"

    if not frappe.db.exists("DocType", old_name):
        return

    if frappe.db.exists("DocType", new_name):
        # Already migrated on this site; nothing to do.
        return

    try:
        frappe.rename_doc("DocType", old_name, new_name, force=True)
        frappe.db.commit()
    except Exception:
        frappe.log_error(
            title="VIsitor Purpose rename failed",
            message=frappe.get_traceback()
        )

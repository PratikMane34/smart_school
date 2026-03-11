@frappe.whitelist()
def get_workspace_data():
    """
    Get the workspace data for the current user.
    """
    user = frappe.session.user
    workspace = frappe.get_doc("Workspace", user)
    return workspace.to_dict()
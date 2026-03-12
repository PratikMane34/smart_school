import frappe

@frappe.whitelist()
def get_workspace_data():
    """
    Get the workspace data for the current user.
    """
    user = frappe.session.user
    workspace = frappe.get_doc("Workspace", user)
    return workspace.to_dict()

@frappe.whitelist()
def get_sidebar():
    menus = frappe.get_all(
        "Sidebar Menu",
        filters={"enabled": 1},
        fields=["name", "menu_name", "route", "icon", "parent_sidebar_menu", "lft","roles"],
        order_by="lft asc"
    )

    tree = {}
    result = []
    
    for m in menus:
        m["children"] = []
        m["roles"] = m["roles"].split(",") if m["roles"] else []
        m["roles"] = [role.strip() for role in m["roles"]]
        tree[m["name"]] = m

    for m in menus:
        parent = m["parent_sidebar_menu"]
        if parent and parent in tree:
            tree[parent]["children"].append(m)
        else:
            result.append(m)
        # roles = m["roles"]

    return result
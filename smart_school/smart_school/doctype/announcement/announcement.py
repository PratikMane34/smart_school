import frappe
from frappe.model.document import Document


class Announcement(Document):
    def validate(self):
        if not self.posted_by:
            self.posted_by = frappe.session.user

        if self.valid_to and self.valid_from and self.valid_to < self.valid_from:
            frappe.throw("Valid To cannot be before Valid From")

# Copyright (c) 2026, Pratik Mane and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Timetable(Document):
    def validate(self):
        self.check_date_range()
        self.check_slot_conflicts()

    def check_date_range(self):
        if self.effective_to and self.effective_to < self.effective_from:
            frappe.throw("Effective To must be after Effective From")

    def check_slot_conflicts(self):
        seen = set()
        for row in self.slots:
            key = (row.day, row.period)
            if key in seen:
                frappe.throw(f"Duplicate slot: {row.day} / {row.period}")
            seen.add(key)

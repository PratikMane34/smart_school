import frappe
from smart_school.api._guards import require_role


# ─────────────────────────────────────────────
# Read-only listings over Education's fee doctypes
# ─────────────────────────────────────────────

@frappe.whitelist()
def get_fee_structures(program=None, academic_year=None, academic_term=None,
                       start_page=1, page_size=20):
    """List Fee Structures with optional filters."""
    filters = {}
    if program:
        filters["program"] = program
    if academic_year:
        filters["academic_year"] = academic_year
    if academic_term:
        filters["academic_term"] = academic_term

    start_page = int(start_page)
    page_size = int(page_size)

    structures = frappe.get_all(
        "Fee Structure",
        filters=filters,
        fields=["name", "program", "academic_year", "academic_term",
                "student_category", "total_amount", "receivable_account"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="modified desc"
    )

    return {
        "success": True,
        "message": "Fee structures fetched successfully",
        "data": structures,
        "total": frappe.db.count("Fee Structure", filters=filters),
        "start_page": start_page,
        "page_size": page_size
    }


@frappe.whitelist()
def get_fee_schedules(academic_year=None, academic_term=None, fee_structure=None,
                     start_page=1, page_size=20):
    """List Fee Schedules with optional filters."""
    filters = {}
    if academic_year:
        filters["academic_year"] = academic_year
    if academic_term:
        filters["academic_term"] = academic_term
    if fee_structure:
        filters["fee_structure"] = fee_structure

    start_page = int(start_page)
    page_size = int(page_size)

    schedules = frappe.get_all(
        "Fee Schedule",
        filters=filters,
        fields=["name", "fee_structure", "program", "academic_year",
                "academic_term", "due_date", "posting_date", "total_amount"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="modified desc"
    )

    return {
        "success": True,
        "message": "Fee schedules fetched successfully",
        "data": schedules,
        "total": frappe.db.count("Fee Schedule", filters=filters),
        "start_page": start_page,
        "page_size": page_size
    }


@frappe.whitelist()
def get_fees(student=None, program=None, academic_year=None, academic_term=None,
            outstanding_only=0, start_page=1, page_size=20):
    """
    List Fees with optional filters.

    `outstanding_only=1` restricts the listing to invoices with outstanding amount.
    """
    filters = {}
    if student:
        filters["student"] = student
    if program:
        filters["program"] = program
    if academic_year:
        filters["academic_year"] = academic_year
    if academic_term:
        filters["academic_term"] = academic_term
    if int(outstanding_only or 0):
        filters["outstanding_amount"] = [">", 0]
        filters["docstatus"] = ["!=", 2]

    start_page = int(start_page)
    page_size = int(page_size)

    fees = frappe.get_all(
        "Fees",
        filters=filters,
        fields=["name", "student", "student_name", "program", "academic_year",
                "academic_term", "fee_structure", "fee_schedule",
                "posting_date", "due_date", "grand_total", "outstanding_amount",
                "docstatus"],
        start=(start_page - 1) * page_size,
        page_length=page_size,
        order_by="due_date desc"
    )

    return {
        "success": True,
        "message": "Fees fetched successfully",
        "data": fees,
        "total": frappe.db.count("Fees", filters=filters),
        "start_page": start_page,
        "page_size": page_size
    }


@frappe.whitelist()
def get_outstanding_by_program(academic_year=None):
    """
    Aggregate outstanding amount across all Fees, grouped by program.
    """
    filters = {"outstanding_amount": [">", 0], "docstatus": ["!=", 2]}
    if academic_year:
        filters["academic_year"] = academic_year

    rows = frappe.db.sql(
        """
        SELECT program,
               COUNT(*)                AS invoice_count,
               SUM(grand_total)        AS total_billed,
               SUM(outstanding_amount) AS total_outstanding
        FROM `tabFees`
        WHERE outstanding_amount > 0
          AND docstatus != 2
          {extra}
        GROUP BY program
        ORDER BY total_outstanding DESC
        """.format(extra=("AND academic_year = %(academic_year)s" if academic_year else "")),
        {"academic_year": academic_year} if academic_year else {},
        as_dict=True
    )

    return {
        "success": True,
        "message": "Outstanding fees summary fetched successfully",
        "data": rows
    }


# ─────────────────────────────────────────────
# Action - bulk generate Fees for a Student Group
# ─────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def generate_fees_for_group():
    """
    Generate Fees rows for each student in a Student Group using a given
    Fee Structure.

    POST /api/method/smart_school.api.fees.generate_fees_for_group
    Body: {
        "student_group": "STG-...",
        "fee_structure": "FS-...",
        "academic_year": "2026",
        "academic_term": "Term 1",
        "due_date": "2026-06-30",
        "posting_date": "2026-05-01"   // optional, defaults to today
    }
    """
    require_role("School Admin")

    data = frappe.request.get_json() or {}

    student_group = data.get("student_group")
    fee_structure = data.get("fee_structure")
    due_date = data.get("due_date")

    if not (student_group and fee_structure and due_date):
        frappe.throw("student_group, fee_structure and due_date are required")

    structure = frappe.get_doc("Fee Structure", fee_structure)
    posting_date = data.get("posting_date") or frappe.utils.nowdate()
    academic_year = data.get("academic_year") or structure.academic_year
    academic_term = data.get("academic_term") or structure.academic_term

    students = frappe.get_all(
        "Student Group Student",
        filters={"parent": student_group, "active": 1},
        fields=["student", "student_name"]
    )

    created = []
    skipped = []

    for s in students:
        existing = frappe.db.exists("Fees", {
            "student": s.student,
            "fee_structure": fee_structure,
            "academic_year": academic_year,
            "academic_term": academic_term,
            "docstatus": ["!=", 2],
        })
        if existing:
            skipped.append({"student": s.student, "reason": "Fee already generated"})
            continue

        try:
            fee = frappe.get_doc({
                "doctype": "Fees",
                "student": s.student,
                "student_name": s.student_name,
                "program": structure.program,
                "academic_year": academic_year,
                "academic_term": academic_term,
                "fee_structure": fee_structure,
                "posting_date": posting_date,
                "due_date": due_date,
                "student_category": structure.student_category,
                "components": [
                    {
                        "fees_category": c.fees_category,
                        "amount": c.amount,
                        "description": c.description,
                    }
                    for c in (structure.components or [])
                ],
            })
            fee.insert()
            created.append(fee.name)
        except Exception as e:
            skipped.append({"student": s.student, "reason": str(e)})

    frappe.db.commit()

    return {
        "success": True,
        "message": f"Generated {len(created)} fees ({len(skipped)} skipped)",
        "data": {
            "created": created,
            "skipped": skipped,
        }
    }

# iot_hcm/iot_hcm/api.py
import frappe
from frappe import _
import json
from datetime import datetime
import requests


@frappe.whitelist(allow_guest=True, methods=['POST'])
def sync_attendance_from_external():
    """
    Sync attendance data from external attendance system
    This endpoint will fetch data from the external API and create attendance records
    """
    try:
        # Fetch data from external API
        external_api_url = frappe.db.get_single_value(
            "Attendance Sync Settings", "external_api_url")
        api_limit = frappe.db.get_single_value(
            "Attendance Sync Settings", "sync_limit") or 50
        api_timeout = frappe.db.get_single_value(
            "Attendance Sync Settings", "api_timeout") or 30

        if not external_api_url:
            frappe.throw(
                _("External API URL not configured. Please check Attendance Sync Settings."))

        # Make API call to external system
        response = requests.get(
            f"{external_api_url}?limit={api_limit}", timeout=api_timeout)
        response.raise_for_status()

        external_data = response.json()

        if not external_data.get('data'):
            return {
                "status": "success",
                "message": "No new attendance data found",
                "synced_count": 0
            }

        # Process each attendance record
        synced_count = 0
        errors = []

        for record in external_data['data']:
            try:
                result = process_attendance_record(record)
                if result['created'] or result['updated']:
                    synced_count += 1
            except Exception as e:
                errors.append({
                    "record_id": record.get('id'),
                    "user": record.get('user'),
                    "error": str(e)
                })
                frappe.log_error(frappe.get_traceback(
                ), f"Attendance Sync Error - Record {record.get('id')}")

        return {
            "status": "success",
            "message": f"Successfully synced {synced_count} attendance records",
            "synced_count": synced_count,
            "errors": errors
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Attendance Sync API Error")
        return {
            "status": "error",
            "message": str(e)
        }


def process_attendance_record(record):
    """Process individual attendance record from external system"""

    # Extract data from external record
    external_id = record.get('id')
    user_name = record.get('user')
    date = record.get('date')
    checkin_time = record.get('checkin_time')
    checkout_time = record.get('checkout_time')
    company_name = record.get('company')

    # Find employee by name (you'll need to map this correctly)
    employee = find_employee_by_name(user_name)
    if not employee:
        frappe.throw(_(f"Employee not found for user: {user_name}"))

    # Parse datetime
    attendance_date = datetime.strptime(date, '%Y-%m-%d').date()

    # Check if attendance record already exists
    existing_attendance = frappe.db.get_value(
        "Attendance",
        {
            "employee": employee,
            "attendance_date": attendance_date
        },
        ["name", "docstatus"]
    )

    created = False
    updated = False

    if existing_attendance:
        # Update existing record
        attendance_doc = frappe.get_doc("Attendance", existing_attendance[0])

        # Update fields if needed
        if checkin_time and checkin_time != "Unknown":
            attendance_doc.in_time = f"{date} {checkin_time}"

        if checkout_time and checkout_time != "Unknown":
            attendance_doc.out_time = f"{date} {checkout_time}"

        # Add custom fields for tracking external data
        attendance_doc.custom_external_id = external_id
        attendance_doc.custom_sync_timestamp = frappe.utils.now()

        attendance_doc.save(ignore_permissions=True)
        updated = True

    else:
        # Create new attendance record
        attendance_doc = frappe.get_doc({
            "doctype": "Attendance",
            "employee": employee,
            "attendance_date": attendance_date,
            "status": "Present",  # Always present as per requirement
            # Get from employee master
            "company": get_employee_company(employee),
            "in_time": f"{date} {checkin_time}" if checkin_time and checkin_time != "Unknown" else None,
            "out_time": f"{date} {checkout_time}" if checkout_time and checkout_time != "Unknown" else None,
            "custom_external_id": external_id,
            "custom_sync_timestamp": frappe.utils.now(),
            "custom_external_user_name": user_name,
            "custom_external_company": company_name
        })

        attendance_doc.insert(ignore_permissions=True)
        created = True

    # Submit the document if it's in draft state
    if attendance_doc.docstatus == 0:
        attendance_doc.submit()

    frappe.db.commit()

    return {
        "created": created,
        "updated": updated,
        "attendance_name": attendance_doc.name
    }


def find_employee_by_name(user_name):
    """Find employee by matching name patterns"""

    # Try exact match first
    employee = frappe.db.get_value(
        "Employee", {"employee_name": user_name}, "name")
    if employee:
        return employee

    # Try partial matching (remove common suffixes/prefixes)
    clean_name = user_name.replace("_TESTING", "").replace("_", " ").strip()

    # Search by employee name containing the clean name
    employees = frappe.db.sql("""
        SELECT name FROM `tabEmployee` 
        WHERE employee_name LIKE %s 
        AND status = 'Active'
        LIMIT 1
    """, (f"%{clean_name}%",))

    if employees:
        return employees[0][0]

    # Search by first name
    first_name = clean_name.split()[0] if clean_name else ""
    if first_name:
        employees = frappe.db.sql("""
            SELECT name FROM `tabEmployee` 
            WHERE first_name LIKE %s 
            AND status = 'Active'
            LIMIT 1
        """, (f"%{first_name}%",))

        if employees:
            return employees[0][0]

    return None


def get_employee_company(employee):
    """Get company for employee"""
    company = frappe.db.get_value("Employee", employee, "company")
    return company or frappe.defaults.get_user_default("Company")


@frappe.whitelist(allow_guest=True, methods=['GET'])
def test_external_api():
    """Test endpoint to check external API connectivity"""
    try:
        external_api_url = frappe.db.get_single_value(
            "Attendance Sync Settings", "external_api_url")
        api_timeout = frappe.db.get_single_value(
            "Attendance Sync Settings", "api_timeout") or 30

        if not external_api_url:
            return {
                "status": "error",
                "message": "External API URL not configured"
            }

        response = requests.get(
            f"{external_api_url}?limit=1", timeout=api_timeout)
        response.raise_for_status()

        data = response.json()

        return {
            "status": "success",
            "message": "External API connection successful",
            "sample_data": data.get('data', [])[:1] if data.get('data') else []
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"External API connection failed: {str(e)}"
        }


@frappe.whitelist(allow_guest=True, methods=['POST'])
def manual_sync():
    """Manual sync trigger endpoint"""
    return sync_attendance_from_external()


@frappe.whitelist()
def get_sync_statistics():
    """Get attendance sync statistics for dashboard"""
    try:
        # Get today's synced attendance count
        today_sync_count = frappe.db.count("Attendance", {
            "custom_sync_timestamp": [">=", frappe.utils.today()],
            "custom_external_id": ["!=", ""]
        })

        # Get total synced records
        total_sync_count = frappe.db.count("Attendance", {
            "custom_external_id": ["!=", ""]
        })

        # Get last sync info
        settings = frappe.get_single("Attendance Sync Settings")

        # Get recent sync errors
        recent_errors = frappe.db.sql("""
            SELECT creation, error 
            FROM `tabError Log` 
            WHERE method_name LIKE '%attendance%sync%' 
            ORDER BY creation DESC 
            LIMIT 5
        """, as_dict=True)

        return {
            "today_sync_count": today_sync_count,
            "total_sync_count": total_sync_count,
            "last_sync_time": settings.last_sync_timestamp,
            "last_sync_status": settings.last_sync_status,
            "last_sync_count": settings.last_sync_count,
            "recent_errors": recent_errors
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sync Statistics Error")
        return {
            "error": str(e)
        }

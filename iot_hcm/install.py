# iot_hcm/iot_hcm/install.py
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    """Setup custom fields after app installation"""
    create_attendance_custom_fields()
    create_attendance_sync_settings()
    print("IoT HCM app installed successfully!")


def create_attendance_custom_fields():
    """Add custom fields to Attendance doctype for external sync tracking"""
    custom_fields = {
        "Attendance": [
            {
                "fieldname": "custom_external_sync_section",
                "label": "External Sync Details",
                "fieldtype": "Section Break",
                "insert_after": "late_entry"
            },
            {
                "fieldname": "custom_external_id",
                "label": "External System ID",
                "fieldtype": "Data",
                "insert_after": "custom_external_sync_section",
                "read_only": 1
            },
            {
                "fieldname": "custom_external_user_name",
                "label": "External User Name",
                "fieldtype": "Data",
                "insert_after": "custom_external_id",
                "read_only": 1
            },
            {
                "fieldname": "custom_external_company",
                "label": "External Company",
                "fieldtype": "Data",
                "insert_after": "custom_external_user_name",
                "read_only": 1
            },
            {
                "fieldname": "custom_sync_timestamp",
                "label": "Last Sync Time",
                "fieldtype": "Datetime",
                "insert_after": "custom_external_company",
                "read_only": 1
            }
        ]
    }

    try:
        create_custom_fields(custom_fields, update=True)
        print("Custom fields created successfully for Attendance doctype")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         "Custom Fields Creation Error")
        print(f"Error creating custom fields: {str(e)}")


def create_attendance_sync_settings():
    """Create default Attendance Sync Settings"""
    try:
        if not frappe.db.exists("Attendance Sync Settings", "Attendance Sync Settings"):
            doc = frappe.get_doc({
                "doctype": "Attendance Sync Settings",
                "external_api_url": "https://pre.fiyansa.com/api/attendance-get",
                "sync_limit": 50,
                "api_timeout": 30,
                "auto_sync_enabled": 0,
                "sync_interval": 60,
                "last_sync_status": "Not Started",
                "total_synced_records": 0
            })
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
            print("Attendance Sync Settings created successfully")
        else:
            print("Attendance Sync Settings already exists")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         "Attendance Sync Settings Creation Error")
        print(f"Error creating Attendance Sync Settings: {str(e)}")


def before_uninstall():
    """Cleanup before app uninstall"""
    try:
        # Remove custom fields
        custom_fields = frappe.get_all("Custom Field",
                                       filters={"fieldname": [
                                           "like", "custom_external_%"]},
                                       fields=["name"])

        for field in custom_fields:
            frappe.delete_doc("Custom Field", field.name,
                              ignore_permissions=True)

        # Remove settings
        if frappe.db.exists("Attendance Sync Settings", "Attendance Sync Settings"):
            frappe.delete_doc("Attendance Sync Settings",
                              "Attendance Sync Settings", ignore_permissions=True)

        frappe.db.commit()
        print("IoT HCM app cleanup completed")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "App Uninstall Error")
        print(f"Error during uninstall: {str(e)}")

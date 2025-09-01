# iot_hcm/iot_hcm/tasks.py
import frappe
from iot_hcm.iot_hcm.api import sync_attendance_from_external
import traceback


def sync_attendance_hourly():
    """Scheduled task to sync attendance data every hour"""

    try:
        # Check if auto sync is enabled
        settings = frappe.get_single("Attendance Sync Settings")

        if not settings.auto_sync_enabled:
            frappe.logger().info("Auto sync is disabled. Skipping scheduled sync.")
            return

        frappe.logger().info("Starting scheduled attendance sync...")

        # Run sync
        result = sync_attendance_from_external()

        # Update sync status in settings
        settings.last_sync_timestamp = frappe.utils.now()
        settings.last_sync_status = result.get('status', 'unknown')
        settings.last_sync_count = result.get('synced_count', 0)

        if result.get('status') == 'success':
            settings.total_synced_records = (
                settings.total_synced_records or 0) + result.get('synced_count', 0)
            settings.last_error_message = ""
            frappe.logger().info(
                f"Scheduled sync completed successfully. Synced {result.get('synced_count', 0)} records.")
        else:
            settings.last_error_message = result.get(
                'message', 'Unknown error')
            frappe.logger().error(
                f"Scheduled sync failed: {settings.last_error_message}")

        settings.save(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        # Log error and update settings
        error_msg = str(e)
        frappe.log_error(traceback.format_exc(),
                         "Scheduled Attendance Sync Error")
        frappe.logger().error(f"Scheduled attendance sync error: {error_msg}")

        try:
            settings = frappe.get_single("Attendance Sync Settings")
            settings.last_sync_timestamp = frappe.utils.now()
            settings.last_sync_status = "error"
            settings.last_error_message = error_msg
            settings.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as settings_error:
            frappe.logger().error(
                f"Failed to update sync settings after error: {str(settings_error)}")


def daily_sync_cleanup():
    """Daily task to cleanup old sync logs and maintain data integrity"""

    try:
        frappe.logger().info("Starting daily sync cleanup...")

        # Clean up old error logs related to attendance sync (keep only last 100)
        old_logs = frappe.db.sql("""
            SELECT name FROM `tabError Log` 
            WHERE method_name LIKE '%attendance%sync%' 
            ORDER BY creation DESC 
            LIMIT 18446744073709551615 OFFSET 100
        """)

        if old_logs:
            for log in old_logs:
                frappe.delete_doc("Error Log", log[0], ignore_permissions=True)

        # Update statistics
        settings = frappe.get_single("Attendance Sync Settings")
        total_synced = frappe.db.count(
            "Attendance", {"custom_external_id": ["!=", ""]})
        settings.total_synced_records = total_synced
        settings.save(ignore_permissions=True)

        frappe.db.commit()
        frappe.logger().info("Daily sync cleanup completed successfully")

    except Exception as e:
        frappe.log_error(traceback.format_exc(), "Daily Sync Cleanup Error")
        frappe.logger().error(f"Daily sync cleanup error: {str(e)}")


def test_sync_connection():
    """Test task to verify external API connectivity"""

    try:
        from iot_hcm.iot_hcm.api import test_external_api

        result = test_external_api()

        if result.get('status') == 'success':
            frappe.logger().info("External API connection test successful")
        else:
            frappe.logger().warning(
                f"External API connection test failed: {result.get('message')}")

    except Exception as e:
        frappe.log_error(traceback.format_exc(), "API Connection Test Error")
        frappe.logger().error(f"API connection test error: {str(e)}")


def manual_full_sync():
    """Manual task to perform full sync with higher limits"""

    try:
        frappe.logger().info("Starting manual full sync...")

        # Temporarily increase sync limit for full sync
        settings = frappe.get_single("Attendance Sync Settings")
        original_limit = settings.sync_limit

        # Set higher limit for full sync
        settings.sync_limit = 500
        settings.save(ignore_permissions=True)

        # Run sync
        result = sync_attendance_from_external()

        # Restore original limit
        settings.sync_limit = original_limit
        settings.save(ignore_permissions=True)

        frappe.db.commit()

        frappe.logger().info(f"Manual full sync completed. Result: {result}")

        return result

    except Exception as e:
        frappe.log_error(traceback.format_exc(), "Manual Full Sync Error")
        frappe.logger().error(f"Manual full sync error: {str(e)}")
        return {"status": "error", "message": str(e)}

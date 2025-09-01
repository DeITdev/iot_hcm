# iot_hcm/iot_hcm/doctype/attendance_sync_settings/attendance_sync_settings.py

from frappe.model.document import Document
import frappe
import requests


class AttendanceSyncSettings(Document):
    def validate(self):
        """Validate settings before saving"""
        if self.sync_interval and self.sync_interval < 5:
            frappe.throw("Sync interval cannot be less than 5 minutes")

        if self.sync_limit and self.sync_limit > 1000:
            frappe.throw("Sync limit cannot exceed 1000 records per request")

        if self.api_timeout and self.api_timeout < 5:
            frappe.throw("API timeout cannot be less than 5 seconds")

        # Validate URL format
        if self.external_api_url and not (self.external_api_url.startswith('http://') or self.external_api_url.startswith('https://')):
            frappe.throw(
                "External API URL must start with http:// or https://")

    def test_api_connection(self):
        """Test connection to external API"""
        try:
            response = requests.get(
                f"{self.external_api_url}?limit=1", timeout=self.api_timeout)
            response.raise_for_status()
            data = response.json()

            if 'data' in data:
                frappe.msgprint(
                    "API connection successful! Sample data received.", indicator="green")
                return True
            else:
                frappe.msgprint(
                    "API connection successful but unexpected response format.", indicator="orange")
                return False

        except requests.exceptions.Timeout:
            frappe.msgprint(
                "API connection timed out. Please check the timeout setting.", indicator="red")
            return False
        except requests.exceptions.ConnectionError:
            frappe.msgprint(
                "Could not connect to API. Please check the URL.", indicator="red")
            return False
        except Exception as e:
            frappe.msgprint(
                f"API connection failed: {str(e)}", indicator="red")
            return False

    def trigger_manual_sync(self):
        """Trigger manual sync"""
        from iot_hcm.iot_hcm.api import sync_attendance_from_external

        try:
            result = sync_attendance_from_external()

            if result.get('status') == 'success':
                frappe.msgprint(
                    f"Manual sync completed successfully! Synced {result.get('synced_count', 0)} records.",
                    indicator="green"
                )
            else:
                frappe.msgprint(
                    f"Manual sync failed: {result.get('message', 'Unknown error')}",
                    indicator="red"
                )

            return result

        except Exception as e:
            frappe.msgprint(f"Manual sync error: {str(e)}", indicator="red")
            return {"status": "error", "message": str(e)}

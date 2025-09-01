// iot_hcm/iot_hcm/doctype/attendance_sync_settings/attendance_sync_settings.js

frappe.ui.form.on('Attendance Sync Settings', {
  test_api_btn: function (frm) {
    if (!frm.doc.external_api_url) {
      frappe.msgprint('Please set the External API URL first');
      return;
    }

    frm.call({
      method: 'test_api_connection',
      doc: frm.doc,
      btn: $('.btn-test-api'),
      callback: function (r) {
        if (r.message) {
          console.log('API Test Result:', r.message);
        }
      }
    });
  },

  manual_sync_btn: function (frm) {
    if (!frm.doc.external_api_url) {
      frappe.msgprint('Please set the External API URL first');
      return;
    }

    frappe.show_alert({
      message: 'Starting manual sync...',
      indicator: 'blue'
    });

    frm.call({
      method: 'trigger_manual_sync',
      doc: frm.doc,
      btn: $('.btn-manual-sync'),
      callback: function (r) {
        if (r.message) {
          frm.refresh();
          console.log('Manual Sync Result:', r.message);
        }
      }
    });
  },

  refresh: function (frm) {
    // Auto-refresh sync statistics every 30 seconds when form is open
    if (frm.doc.auto_sync_enabled && !frm.refresh_interval) {
      frm.refresh_interval = setInterval(function () {
        if (frm.is_dirty()) return; // Don't refresh if form is being edited

        frm.call({
          method: 'iot_hcm.iot_hcm.api.get_sync_statistics',
          callback: function (r) {
            if (r.message && !r.message.error) {
              // Update display fields without triggering validation
              frm.set_value('total_synced_records', r.message.total_sync_count);
              frm.refresh_field('total_synced_records');
            }
          }
        });
      }, 30000); // 30 seconds
    }

    // Add custom buttons to toolbar
    if (frm.doc.external_api_url) {
      frm.add_custom_button(__('View Sync Logs'), function () {
        frappe.route_to_list('Error Log', {
          'method_name': ['like', '%attendance%sync%']
        });
      });

      frm.add_custom_button(__('View Synced Attendance'), function () {
        frappe.route_to_list('Attendance', {
          'custom_external_id': ['!=', '']
        });
      });
    }
  },

  onload: function (frm) {
    // Add help text
    frm.set_intro(__('Configure external attendance system integration. The system will automatically sync attendance data from the configured API endpoint.'));

    // Set default values for new documents
    if (frm.is_new()) {
      frm.set_value('external_api_url', 'https://pre.fiyansa.com/api/attendance-get');
      frm.set_value('sync_limit', 50);
      frm.set_value('api_timeout', 30);
      frm.set_value('sync_interval', 60);
    }
  },

  before_save: function (frm) {
    // Clear refresh interval before saving
    if (frm.refresh_interval) {
      clearInterval(frm.refresh_interval);
      frm.refresh_interval = null;
    }
  }
});
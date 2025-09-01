# iot_hcm/hooks.py
app_name = "iot_hcm"
app_title = "Iot Hcm"
app_publisher = "danar"
app_description = "iot"
app_email = "danarikram@gmail.com"
app_license = "mit"

# Installation hooks temporarily commented out
# after_install = "iot_hcm.iot_hcm.install.after_install"
# before_uninstall = "iot_hcm.iot_hcm.install.before_uninstall"

# Scheduled Tasks
scheduler_events = {
    "hourly": [
        "iot_hcm.iot_hcm.tasks.sync_attendance_hourly"
    ],
    "daily": [
        "iot_hcm.iot_hcm.tasks.daily_sync_cleanup"
    ]
}

# Fixtures
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["fieldname", "in", [
                "custom_external_sync_section",
                "custom_external_id",
                "custom_external_user_name",
                "custom_external_company",
                "custom_sync_timestamp"
            ]]
        ]
    }
]

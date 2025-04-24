from . import __version__ as app_version

app_name = "whatsapp_erpnext"
app_title = "WhatsApp ERPNext"
app_publisher = "Finbyz Tech Pvt. Ltd."
app_description = "WhatsApp integration with ERPNext"
app_email = "info@finbyz.tech"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/whatsapp_erpnext/css/whatsapp_erpnext.css"
# app_include_js = "/assets/whatsapp_erpnext/js/whatsapp_erpnext.js"

# include js, css files in header of web template
# web_include_css = "/assets/whatsapp_erpnext/css/whatsapp_erpnext.css"
# web_include_js = "/assets/whatsapp_erpnext/js/whatsapp_erpnext.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "whatsapp_erpnext/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Sales Invoice" : "public/js/sales_invoice.js",
    "Payment Entry" : "public/js/payment_entry.js",
    "Sales Order" : "public/js/sales_order.js",
    "Quotation" : "public/js/quotation.js",
    "Purchase Order" : "public/js/purchase_order.js",
    "Delivery Note" : "public/js/delivery_note.js",
    "Issue": "public/js/issue.js",
    "Notification" : "public/js/notificaton.js",
    }
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "whatsapp_erpnext.utils.jinja_methods",
#	"filters": "whatsapp_erpnext.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "whatsapp_erpnext.install.before_install"
# after_install = "whatsapp_erpnext.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "whatsapp_erpnext.uninstall.before_uninstall"
# after_uninstall = "whatsapp_erpnext.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "whatsapp_erpnext.utils.before_app_install"
# after_app_install = "whatsapp_erpnext.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "whatsapp_erpnext.utils.before_app_uninstall"
# after_app_uninstall = "whatsapp_erpnext.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "whatsapp_erpnext.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Notification": "whatsapp_erpnext.override.notification.Notification"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Notification": {
		"on_trash": "whatsapp_erpnext.whatsapp_erpnext.doc_events.notification.on_trash",
        "validate": "whatsapp_erpnext.whatsapp_erpnext.doc_events.notification.validate",
        "after_insert": "whatsapp_erpnext.whatsapp_erpnext.doc_events.notification.after_insert"
	},
    "*": {
        "before_insert": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "after_insert": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "before_validate": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "validate": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "on_update": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "before_submit": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "on_submit": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "before_cancel": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "on_cancel": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "on_trash": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "after_delete": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "before_update_after_submit": "whatsapp_erpnext.utils.run_server_script_for_doc_event",
        "on_update_after_submit": "whatsapp_erpnext.utils.run_server_script_for_doc_event"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "all": [
        "whatsapp_erpnext.schedule.schedule_whatsapp_comments",
        "whatsapp_erpnext.schedule.bg_message_contact_generation",
        "whatsapp_erpnext.schedule.retry_failed_whatsapp_messages",
    ],
}

# Testing
# -------

# before_tests = "whatsapp_erpnext.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "whatsapp_erpnext.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "whatsapp_erpnext.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["whatsapp_erpnext.utils.before_request"]
# after_request = ["whatsapp_erpnext.utils.after_request"]

# Job Events
# ----------
# before_job = ["whatsapp_erpnext.utils.before_job"]
# after_job = ["whatsapp_erpnext.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"whatsapp_erpnext.auth.validate"
# ]

fixtures = [
	{
         "dt": "Custom Field", 
         "filters":[["module", "=", 'WhatsApp ERPNext']]
    },
    {
         "dt": "Property Setter", 
         "filters":[["module", "=", 'WhatsApp ERPNext']]
    },
    {
         "dt": "Role", 
         "filters":[["name", "=", 'WhatsApp Manager']]
    }
    ]
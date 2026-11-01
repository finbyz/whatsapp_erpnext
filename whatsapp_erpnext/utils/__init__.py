"""Run on each event."""
import frappe

from frappe.core.doctype.server_script.server_script_utils import EVENT_MAP
from whatsapp_erpnext.whatsapp_erpnext.doc_events.notification import send_template_message


def run_server_script_for_doc_event(doc, event):
    """Run on each event."""
    if event not in EVENT_MAP:
        return

    if frappe.flags.in_install:
        return

    if frappe.flags.in_migrate:
        return

    notification = get_notifications_map().get(
        doc.doctype, {}
    ).get(event, None)

    if notification:
        # run all scripts for this doctype + event
        for notification_name in notification:
            noti_doc = frappe.get_doc(
                "Notification",
                notification_name
            )
            send_template_message(noti_doc, doc)


def get_notifications_map():
    """Get mapping."""
    if frappe.flags.in_patch and not frappe.db.table_exists("Notification"):
        return {}

    notification_map = {}
    enabled_whatsapp_notifications = frappe.get_all(
        "Notification",
        fields=("name", "document_type", "event", "method"),
        filters={"enabled": 1},
    )

    for notification in enabled_whatsapp_notifications:
        if notification.event == "Method":
            notification.event = notification.method
        notification_map.setdefault(
            notification.document_type, {}
        ).setdefault(
            notification.event, []
        ).append(notification.name)

    frappe.cache().set_value("whatsapp_notification_map", notification_map)

    return notification_map

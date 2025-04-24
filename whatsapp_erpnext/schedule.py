import json
import frappe
from frappe.integrations.utils import make_post_request
from frappe.utils.background_jobs import enqueue
from whatsapp_erpnext.whatsapp_erpnext.doc_events.notification import save_whatsapp_log
def schedule_whatsapp_comments():
    message = frappe.db.get_list(
        "WhatsApp Message",
        {
            "comment": ('is','not set'),
            # "to":("is",'set'),
            # "from":("is",'set'),
        },
        order_by="message_datetime ASC",
        page_length=100,
    )

    for msg in message:
        doc = frappe.get_doc("WhatsApp Message", msg.name)

        if doc.type == "Outgoing":
            content = generate_html_message(doc.document_name, doc.doctype_link_name, doc.message)
            # print(content)
        elif doc.type == "Incoming":
            content = doc.message
            # print(content)  
        else:
            continue
        # comment_text = doc.get_comment_text(whatsapp_message_url)
        comment = frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Comment",
                "reference_doctype": doc.link_to,
                "reference_name": doc.link_name,
                "comment_by": frappe.session.user,
                "subject": doc.type,
                "content": content,
            }
        )
        
        comment.save()
        # frappe.db.set_value('Comment',comment.name, 'creation', doc.message_datetime)
        doc.comment = comment.name
        doc.flags.ignore_mandatory = True
        doc.save()

def generate_html_message(doctype_link_name, document_name, message):
    base_url = frappe.utils.get_url()

    if doctype_link_name:
        doctype_slug = doctype_link_name.lower().replace(" ", "-")
    else:
        doctype_slug = "unknown-doctype"

    if document_name:
        document_link = f"{base_url}/app/{doctype_slug}/{document_name}"
        formatted_message = f"""
        <b>Whatsapp Message Sent for <a href="{document_link}" target="_blank">{doctype_link_name} - {document_name}</a></b><br>
        {message}
        """
    else:
        formatted_message = f"""
        <b>Whatsapp Message Sent for {doctype_link_name if doctype_link_name else ''}</b><br>
        {message}
        """
    
    return formatted_message

def bg_message_contact_generation():
    message = frappe.db.get_list(
        "WhatsApp Message",
        filters={
            "contact_not_found": 0  # Only include unchecked
        },
        or_filters=[
            {"link_to": ('is', 'not set')},
            {"link_name": ('is', 'not set')},
            {"contact": ('is', 'not set')}
        ],
        fields=["name", "to", "from"],
        limit=50
    )
    for msg in message:
        contact = msg.get("to") if msg.get("to") else msg.get("from")
        contact_query = f"""
                        SELECT 
                            c.name, 
                            dl.link_doctype, 
                            dl.link_name 
                            FROM 
                                `tabContact` AS c 
                            JOIN 
                                `tabContact Phone` AS cp 
                                ON cp.parent = c.name 
                            JOIN 
                                `tabDynamic Link` AS dl 
                                ON dl.parent = c.name 
                            WHERE 
                                LENGTH(cp.phone) >= 10
                                AND cp.phone = '{contact}'
                            ORDER BY 
                            CASE dl.link_doctype
                                WHEN 'Customer' THEN 1
                                WHEN 'Lead' THEN 2
                                ELSE 3
                            END,
                            c.modified DESC
                        LIMIT 1;
                    """
        contact_details = frappe.db.sql(contact_query, as_dict=True)
        whatsapp_message = frappe.get_doc("WhatsApp Message", msg.get("name"))
        if not contact_details:
            whatsapp_message.contact_not_found = 1
            whatsapp_message.save(ignore_permissions=True)
            continue
        # print(contact_details)
        
        whatsapp_message.link_to = contact_details[0].get("link_doctype", "")
        whatsapp_message.link_name = contact_details[0].get("link_name", "")
        whatsapp_message.contact = contact_details[0].get("name", "")
        whatsapp_message.save()
        
def retry_failed_whatsapp_messages():
    """Retry sending failed WhatsApp messages."""
    settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
    failed_messages = frappe.get_list("WhatsApp Message", filters={"status": "Failed","retry_count":["<",5]}, fields=["name"], limit_page_length=50)

    for message in failed_messages:
        whatsapp_msg = frappe.get_doc("WhatsApp Message", message.name)
        
        data = prepare_retry_data(whatsapp_msg)
        if not data:
            continue
        token = settings.get_password("token")

        headers = {
            "authorization": f"Bearer {token}",
            "content-type": "application/json"
        }

        response = make_post_request(
            f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
            headers=headers,
            data=json.dumps(data),
        )

        whatsapp_msg.rejection_remakrs = ""
        whatsapp_msg.retry_count += 1
        if "messages" in response and response["messages"]:
            message_id = response["messages"][0]["id"]
            whatsapp_msg.message_id = message_id
            whatsapp_msg.error_field = str(response)  
            whatsapp_msg.save(ignore_permissions=True)  # Save changes
            frappe.msgprint(f"WhatsApp message {whatsapp_msg.name} retried successfully", indicator="green", alert=False)
            enqueue(save_whatsapp_log, self=whatsapp_msg, data=data, message_id=message_id, label=whatsapp_msg.label)

        
def prepare_retry_data(whatsapp_msg):
    if not whatsapp_msg.mesaage_data:
        return

    error_field = json.loads(whatsapp_msg.error_field.replace("'", '"'))
    statuses = error_field.get("statuses", [])

    for status in statuses:
        if status.get("status") == "failed":
            errors = status.get("errors", [])
            for error in errors:
                if error.get("code") == 131026:
                    return None  # Return None to skip retry if specific error code found

    mesaage_data = json.loads(whatsapp_msg.mesaage_data.replace("'", '"'))
    return {
        "messaging_product": "whatsapp",
        "to": whatsapp_msg.to,
        "type": "template",
        "template": {
            "name": mesaage_data['name'],
            "language": mesaage_data['language'],
            "components": mesaage_data['components'],
        },
    }

import json
import frappe ,re
from frappe.model.document import Document
from frappe.utils.safe_exec import get_safe_globals, safe_exec
from frappe.integrations.utils import make_post_request
from frappe.desk.form.utils import get_pdf_link
from frappe.utils.background_jobs import enqueue


def validate(self, method):
    if self.channel == "WhatsApp":
        fields = frappe.get_doc("DocType", self.document_type).fields
        fields += frappe.get_all(
            "Custom Field", filters={"dt": self.document_type}, fields=["fieldname"]
        )
        # if not any(field.fieldname == self.custom_receiver_mobile for field in fields): # noqa
        # 	frappe.throw(f"Field name {self.custom_receiver_mobile} does not exists")


def on_trash(self, method):
    pass
    # if self.channel == "WhatsApp":
    # 	if self.notification_type == "Scheduler Event":
    # 		frappe.delete_doc("Scheduled Job Type", self.name)

    # 	frappe.cache().delete_value("whatsapp_notification_map")


def after_insert(self, method):
    pass
    # if self.channel == "WhatsApp":
    # 	if self.notification_type == "Scheduler Event":
    # 		method = f"whatsapp_erpnext.utils.trigger_whatsapp_notifications_{self.event_frequency.lower().replace(' ', '_')}" # noqa
    # 		job = frappe.get_doc(
    # 			{
    # 				"doctype": "Scheduled Job Type",
    # 				"method": method,
    # 				"frequency": self.event_frequency
    # 			}
    # 		)

    # 		job.insert()


def format_number(self, number):
    if number.startswith("+"):
        number = number[1 : len(number)]

    return number


def send_scheduled_message(self) -> dict:
    safe_exec(self.condition, get_safe_globals(), dict(doc=self))
    language_code = frappe.db.get_value(
        "WhatsApp Templates", self.template, fieldname="language_code"
    )
    if language_code:
        for contact in self._contact_list:
            data = {
                "messaging_product": "whatsapp",
                "to": self.format_number(contact),
                "type": "template",
                "template": {
                    "name": self.template,
                    "language": {"code": language_code},
                    "components": [],
                },
            }

            self.notify(data)
    # return _globals.frappe.flags


def send_template_message(self, doc: Document, contact_no=None):
    """Specific to Document Event triggered Server Scripts."""
    if not self.enabled:
        return

    doc_data = doc.as_dict()
    if self.condition:
        # check if condition satisfies
        if not frappe.safe_eval(self.condition, get_safe_globals(), dict(doc=doc_data)):
            return

    template = frappe.db.get_value(
        "WhatsApp Templates", self.custom_whatsapp_template, fieldname="*"
    )

    if template:
        for row in self.recipients:
            if row.receiver_by_document_field != "owner":
                if not contact_no:
                    contact_no = doc.get(row.receiver_by_document_field)
                if contact_no:
                    # Get contact details from phone number
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
                            AND cp.phone = '{contact_no}'
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
                    error_field = ""

                    link_to = ""
                    link_name = ""
                    contact_name = ""
                    if contact_details:
                        contact = contact_details[0]
                        link_to = contact.get("link_doctype", "")
                        link_name = contact.get("link_name", "")
                        contact_name = contact.get("name", "")

                    data = {
                        "messaging_product": "whatsapp",
                        "to": contact_no,
                        "link_to": link_to,
                        "link_name": link_name,
                        "contact": contact_name,
                        "document_name": doc_data["doctype"],
                        "doctype_link_name": doc_data["name"],
                        "message_datetime": frappe.utils.now(),
                        "date": frappe.utils.today(),
                        "error_field": error_field,
                        "type": "template",
                        "template": {
                            "name": self.custom_whatsapp_template,
                            "language": {"code": template.language_code},
                            "components": [],
                        },
                    }

                    # Pass parameter values
                    if self.fields:
                        parameters = []
                        for field in self.fields:
                            parameters.append({
								"type": "text",
								"text": doc.get_formatted(field.field_name)
							})
                        data['template']["components"] = [{
							"type": "body",
							"parameters": parameters
						}]

                    label = None
                    if self.attach_print:
                        key = doc.get_document_share_key()
                        frappe.db.commit()

                        link = get_pdf_link(
                            doc_data["doctype"],
                            doc_data["name"],
                            print_format=self.print_format or "Standard",
                        )

                        filename = f'{doc_data["name"]}.pdf'
                        url = f"{frappe.utils.get_url()}{link}&key={key}"

                        data["template"]["components"].append(
                            {
                                "type": "header",
                                "parameters": [
                                    {
                                        "type": "document",
                                        "document": {"link": url, "filename": filename},
                                    }
                                ],
                            }
                        )
                        label = f"{doc_data['doctype']} - {doc_data['name']}"

                    notify(self, data, label)

def notify(self, data, label=None):
    """Notify."""
    settings = frappe.get_doc(
        "WhatsApp Settings",
        "WhatsApp Settings",
    )
    token = settings.get_password("token")

    headers = {"authorization": f"Bearer {token}", "content-type": "application/json"}
    # try:
    response = make_post_request(
        f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
        headers=headers,
        data=json.dumps(data),
    )

    # error_log = frappe.log_error(message=str(response), title="WhatsApp Message Response")
    data["error_field"] = str(response)  # Save the message in the error_field

        # frappe.log_error(message=str(response), title="WhatsApp Message Triggered")
        # frappe.log_error(message=str(data), title="WhatsApp Message Data")

    message_id = response["messages"][0]["id"]
    enqueue(save_whatsapp_log,self=self, data=data, message_id=message_id, label=label)

    # message_id = response["messages"][0]["id"]
    # enqueue(save_whatsapp_log,self=self, data=data, message_id=message_id, label=label)

    frappe.msgprint("WhatsApp Message Triggered", indicator="green", alert=False)

    # except Exception as e:
    #     response = frappe.flags.integration_request.json()["error"]
    #     error_message = response.get("Error", response.get("message"))
    #     frappe.msgprint(
    #         f"Failed to trigger whatsapp message: {error_message}",
    #         indicator="red",
    #         alert=True,
    #     )
    # finally:
    #     status_response = frappe.flags.integration_request.json().get("error")
    #     frappe.get_doc(
    #         {
    #             "doctype": "Integration Request",
    #             "integration_request_service": self.custom_whatsapp_template,
    #             "output": str(frappe.flags.integration_request.json()),
    #             "status": "Failed" if status_response else "Completed",
    #         }
    #     ).insert(ignore_permissions=True)


def format_number(self, number):
    if number.startswith("+"):
        number = number[1 : len(number)]

    return number

@frappe.whitelist()
def send_notification(notification, ref_doctype, ref_docname, mobile_no=None):
    noti_doc = frappe.get_doc("Notification", notification)
    ref_doc = frappe.get_doc(ref_doctype, ref_docname)

    send_template_message(noti_doc, ref_doc, mobile_no)

# format_message function start
def format_message(data):
    template = data.get("template", {})
    components = template.get("components", [])
    
    message_parts = []
    
    # Process body parameters
    body_components = next((comp for comp in components if comp.get("type") == "body"), None)
    if body_components:
        body_parameters = body_components.get("parameters", [])
        for param in body_parameters:
            if param.get("type") == "text":
                message_parts.append(param.get("text", ""))
    
    return " , ".join(message_parts)
# format_message function end 

def save_whatsapp_log(self, data, message_id, label=None):
    # format_message function start
    formatted_message = format_message(data)
    
    # Get template components and extract body parameters
    template = data.get("template", {})
    components = template.get("components", [])
    body_components = next((comp for comp in components if comp.get("type") == "body"), None)
    message_parts = []
    if body_components:
        body_parameters = body_components.get("parameters", [])
        for param in body_parameters:
            if param.get("type") == "text":
                message_parts.append(param.get("text", ""))
    
    # Function to replace placeholders with values
    def replace_placeholders(template, values):
        # replace {} to parameter index in message
        for index, value in enumerate(values):
            template = re.sub(r'\{\{' + str(index) + r'\}\}', value, template, count=1)
        
        return template
    
    # Combine formatted_message and message_parts
    all_message_parts = [formatted_message] + message_parts
    complete_message = replace_placeholders(self.message, all_message_parts)
    # format_message function end 

    notification = None
    try:
        if self.doctype == "Notification":
            notification = self.name
        elif self.doctype == "WhatsApp Message":
            notification = frappe.get_value("WhatsApp Message", self.name, 'notification')
    except Exception:
        pass

    # Save the WhatsApp message document
    whatsapp_message = frappe.get_doc({
        "doctype": "WhatsApp Message",
        "type": "Outgoing",
        "mesaage_data": str(data.get("template", "")),
        "message": complete_message,
        "to": data.get("to"),
        "link_to": data.get("link_to"),
        "link_name": data.get("link_name"),
        "contact": data.get("contact"),
        "message_datetime": data.get("message_datetime"),
        "date": data.get("date"),
        "message_type": "Template",
        "message_id": message_id,
        "content_type": "document",
        "label": label,
        "document_name": data.get("document_name"),
        "doctype_link_name": data.get("doctype_link_name"),
        "error_field": data.get("error_field"),
        "notification": notification,
    })
    whatsapp_message.save(ignore_permissions=True)

@frappe.whitelist()
def retry_message(whatsapp_msg_id):
    """Retry sending a WhatsApp message based on message ID."""
    settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
    
    whatsapp_msg = frappe.get_doc("WhatsApp Message", whatsapp_msg_id)
    notification = frappe.get_doc("Notification", whatsapp_msg.notification)
    data = prepare_retry_data(whatsapp_msg)
    if not data:
        return
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

    if "messages" in response and response["messages"]:
        message_id = response["messages"][0]["id"]
        whatsapp_msg.message_id = message_id 
        whatsapp_msg.error_field = str(response)  
        whatsapp_msg.rejection_remakrs = ""  # Clear rejection remarks
        whatsapp_msg.save(ignore_permissions=True)  # Save changes
        frappe.msgprint("WhatsApp message retried successfully", indicator="green", alert=False)
    else:
        frappe.msgprint("Failed to retry WhatsApp message", indicator="red", alert=True)

def prepare_retry_data(whatsapp_msg):
    if not whatsapp_msg.mesaage_data:
        frappe.throw("Message data not found in WhatsApp message")
    error_field = json.loads(whatsapp_msg.error_field.replace("'", '"'))
    statuses = error_field.get("statuses", [])
    for status in statuses:
        if status.get("status") == "failed":
            errors = status.get("errors", [])
            for error in errors:
                if error.get("code") == 131026:
                    return

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

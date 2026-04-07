"""Webhook."""
import frappe
import json
import requests
import time
from frappe.utils import get_site_name
from werkzeug.wrappers import Response
import frappe.utils
from datetime import datetime
import pytz
from frappe.utils import cint

settings = frappe.get_doc(
			"WhatsApp Settings", "WhatsApp Settings",
		)
token = settings.get_password("token")
url = f"{settings.url}/{settings.version}/"
bench_location = frappe.utils.get_bench_path()
site_name = get_site_name(frappe.local.request.host)

@frappe.whitelist(allow_guest=True)
def webhook():
	"""Meta webhook."""
	if frappe.request.method == "GET":
		return get()
	return post()


def get():
	"""Get."""
	hub_challenge = frappe.form_dict.get("hub.challenge")
	webhook_verify_token = frappe.db.get_single_value(
		"WhatsApp Settings", "webhook_verify_token"
	)

	if frappe.form_dict.get("hub.verify_token") != webhook_verify_token:
		frappe.throw("Verify token does not match")

	return Response(hub_challenge, status=200)

def post():
	"""Post."""
	data = frappe.request.get_json()
	error_field = ""
	# error_log = frappe.log_error(message=str(data), title="Webhook Data")
	error_field  = str(data)

	if data:
		frappe.get_doc({
			"doctype": "Integration Request",
			"template": "Webhook",
			"meta_data": json.dumps(data)
		}).insert(ignore_permissions=True)


	messages = []
	try:
		messages = data["entry"][0]["changes"][0]["value"].get("messages", [])
	except KeyError:
		messages = data["entry"]["changes"][0]["value"].get("messages", [])

	if messages:
		for message in messages:
			contact_no = message.get('from')
			if contact_no:
					short_contact_no = contact_no[-10:]
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
                        AND (cp.phone = '{contact_no}' OR cp.phone LIKE '%{short_contact_no}')
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

			link_to = ""
			link_name = ""
			contact_name = ""
			if contact_details:
				contact = contact_details[0]
				link_to = contact.get("link_doctype", "")
				link_name = contact.get("link_name", "")
				contact_name = contact.get("name", "")
			# else:
				# Log if no contact is found
				# frappe.log_error(message=f"No contact found for phone number: {contact_no}", title="Contact Not Found")
			message_type = message['type']
			messaage_datetime = datetime.fromtimestamp(cint(message['timestamp']))
			
			if message_type == 'text':
				frappe.get_doc({
					"doctype": "WhatsApp Message",
					"type": "Incoming",
					"from": message['from'],
					"message_datetime": messaage_datetime,
					"date": messaage_datetime.date(),
					"link_to": link_to,
					"link_name": link_name,
					"contact": contact_name,
					"message": message['text']['body'],
					"message_id": message['id'],
					"content_type":message_type,
					"error_field": str(data),
					"status": "Received"
				}).insert(ignore_permissions=True)
			
			elif message_type in ["image", "audio", "video", "document"]:
				media_id = message[message_type]["id"]
				headers = {
					'Authorization': 'Bearer ' + token
				}
				response = requests.get(f'{url}{media_id}/', headers=headers)

				if response.status_code == 200:
					media_data = response.json()
					media_url = media_data.get("url")
					mime_type = media_data.get("mime_type")
					file_extension = mime_type.split('/')[1]

					media_response = requests.get(media_url, headers=headers)
					if media_response.status_code == 200:
						file_data = media_response.content
						time.sleep(1)

						file_name= message.get('document', {}).get('filename', None) or f"{messaage_datetime}.{file_extension}"

						whatsapp_message_doc = frappe.get_doc({
							"doctype": "WhatsApp Message",
							"type": "Incoming",
							"from": message['from'],
							"message_datetime": messaage_datetime,
							"date": messaage_datetime.date(),
							"link_to": link_to,
							"link_name": link_name,
							"contact": contact_name,
							"error_field": error_field,
							"message_id": message['id'],
							"file_name": file_name,
							# "message": f"/files/{file_name}",
							# "attach" : f"/files/{file_name}",
							"content_type": message_type,
							"status": "Received"
						}).insert(ignore_permissions=True)


						file_doc = frappe.get_doc(
							{
								"doctype": "File",
								"attached_to_doctype": "WhatsApp Message",
								"attached_to_name": whatsapp_message_doc.name,
								"attached_to_field": "attach",
								"file_name": file_name,
								"is_private": cint(1),
								"content": file_data,
							}
						).save(ignore_permissions=True)

						whatsapp_message_doc.db_set("attach", file_doc.file_url, update_modified=False)
						whatsapp_message_doc.db_set("message", file_doc.file_url, update_modified=False)

	else:
		changes = None
		try:
			changes = data["entry"][0]["changes"][0]
		except KeyError:
			changes = data["entry"]["changes"][0]
		update_status(changes)
	return


def update_status(data):
	"""Update status hook."""
	if data.get("field") == "message_template_status_update":
		update_template_status(data['value'])

	elif data.get("field") == "messages":
		update_message_status(data['value'])


def update_template_status(data):
	"""Update template status."""
	frappe.db.sql(
		"""UPDATE `tabWhatsApp Templates`
		SET status = %(event)s
		WHERE id = %(message_template_id)s""",
		data
	)

error_codes = {
    1: "Invalid request or possible server error.",
    2: "Temporary due to downtime or due to being overloaded.",
    33: "The business phone number has been deleted.",
    100: "The request included one or more unsupported or misspelled parameters.",
    130472: "Message was not sent as part of an experiment.",
    131000: "Message failed to send due to an unknown error.",
    131005: "Permission is either not granted or has been removed.",
    131008: "The request is missing a required parameter.",
    131009: "One or more parameter values are invalid.",
    131016: "A service is temporarily unavailable.",
    131021: "Sender and recipient phone number is the same.",
    131026: "Unable to deliver message. Reasons can include:\n"
           "  * The recipient phone number is not a WhatsApp phone number.\n"
           "  * Sending an authentication template to a WhatsApp user who has a +91 country calling code (India). Authentication templates currently cannot be sent to WhatsApp users in India.\n"
           "  * Recipient has not accepted our new Terms of Service and Privacy Policy.\n"
           "  * Recipient using an old WhatsApp version; must use the following WhatsApp version or greater:\n"
           "    * Android: 2.21.15.15\n"
           "    * SMBA: 2.21.15.15\n"
           "    * iOS: 2.21.170.4\n"
           "    * SMBI: 2.21.170.4\n"
           "    * KaiOS: 2.2130.10\n"
           "    * Web: 2.2132.6",
    131042: "There was an error related to your payment method.",
    131045: "Message failed to send due to a phone number registration error.",
    131047: "More than 24 hours have passed since the recipient last replied to the sender number.",
    131049: "This message was not delivered to maintain healthy ecosystem engagement.",
    131051: "Unsupported message type.",
    131052: "Unable to download the media sent by the user.",
    131053: "Unable to upload the media used in the message.",
    131057: "Business Account is in maintenance mode.",
    132000: "The number of variable parameter values included in the request did not match the number of variable parameters defined in the template.",
    132001: "The template does not exist in the specified language or the template has not been approved.",
    132005: "Translated text is too long.",
    132007: "Template content violates a WhatsApp policy.",
    132012: "Variable parameter values formatted incorrectly.",
    132015: "Template is paused due to low quality so it cannot be sent in a template message.",
    132016: "Template has been paused too many times due to low quality and is now permanently disabled.",
    132068: "Flow is in blocked state.",
    132069: "Flow is in throttled state and 10 messages using this flow were already sent in the last hour.",
    133000: "A previous deregistration attempt failed.",
    133004: "Server is temporarily unavailable.",
    133005: "Two-step verification PIN incorrect.",
    133006: "Phone number needs to be verified before registering.",
    133008: "Too many two-step verification PIN guesses for this phone number.",
    133009: "Two-step verification PIN was entered too quickly.",
    133010: "Phone number not registered on the WhatsApp Business Platform.",
    133015: "The phone number you are attempting to register was recently deleted, and deletion has not yet completed.",
    135000: "Message failed to send because of an unknown error with your request parameters."
}

def update_message_status(data, ):
	"""Update message status."""
	id = data['statuses'][0]['id']
	status = data['statuses'][0]['status']
	conversation = data['statuses'][0].get('conversation', {}).get('id')
	name = frappe.db.get_value("WhatsApp Message", filters={"message_id": id})

	doc = frappe.get_doc("WhatsApp Message", name)
	if doc.type != "Incoming":
		doc.status = status.title()
	if conversation:
		doc.conversation_id = conversation
	if status == "failed":
		doc.error_field = str(data)
	error_details = ""
	if 'statuses' in data and len(data['statuses']) > 0 and data['statuses'][0]['status'] == 'failed':
		errors = data['statuses'][0]['errors']
		for error in errors:
			reason = error_codes.get(error['code'], "Unknown error")
			error_details += f"{reason}\n"
		doc.rejection_remarks = error_details
	doc.save(ignore_permissions=True)
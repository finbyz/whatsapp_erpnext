# Copyright (c) 2023, Finbyz Tech Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.integrations.utils import make_post_request
from frappe import _

class WhatsAppMessage(Document):
	def before_insert(self):
		if self.type == 'Outgoing' and self.message_type != 'Template':
			if self.attach and not self.attach.startswith("http"):
				link = frappe.utils.get_url() + '/'+ self.attach
			else:
				link = self.attach

			data = {
				"messaging_product": "whatsapp",
				"to": self.format_number(self.to),
				"type": self.content_type
			}
			if self.content_type in ['document', 'image', 'video']:
				data[self.content_type.lower()] = {
					"link": link,
					"filename": self.file_name,
					"caption": self.message
				}
			elif self.content_type == "text":
				data["text"] = {
					"preview_url": True,
					"body": self.message
				}

			elif self.content_type == "audio":
				data["text"] = {
					"link": link
				}

			try:
				self.notify(data)
				self.status = "Success"
			except Exception as e:
				self.status = "Failed"
				frappe.throw(f"Failed to send message {str(e)}")

	def notify(self, data):
		"""Notify."""
		settings = frappe.get_doc(
			"WhatsApp Settings", "WhatsApp Settings",
		)
		token = settings.get_password("token")

		headers = {
			"authorization": f"Bearer {token}",
			"content-type": "application/json"
		}
		try:
			response = make_post_request(
				f"{settings.url}/{settings.version}/{settings.phone_id}/messages",
				headers=headers, data=json.dumps(data)
			)
			self.message_id = response['messages'][0]['id']

		except Exception as e:
			res = frappe.flags.integration_request.json()['error']
			error_message = res.get('Error', res.get("message"))
			frappe.get_doc({
				"doctype": "Integration Request",
				"integration_request_service": "WhatsApp",
				"output": "Text Message",
				"error": frappe.flags.integration_request.json()
			}).insert(ignore_permissions=True)

			frappe.throw(
				msg=error_message,
				title=res.get("error_user_title", "Error")
			)

	def format_number(self, number):
		"""Format number."""
		if number.startswith("+"):
			number = number[1:len(number)]

		return number

@frappe.whitelist()
def get_chats():
	"""
	Get unique chat conversations with latest message and unread count.
	Uses the 'type' field to reliably identify the contact number:
	  - Incoming: contact is in `from`
	  - Outgoing: contact is in `to`
	"""
	chats = frappe.db.sql("""
		SELECT
			CASE
				WHEN wm.type = 'Incoming' THEN wm.`from`
				ELSE wm.`to`
			END as contact_number,
			wm.contact,
			wm.link_to as party_type,
			wm.link_name as party,
			MAX(wm.name) as chat_id,
			MAX(wm.message) as last_message,
			MAX(wm.creation) as last_activity,
			SUM(CASE WHEN wm.type = 'Incoming' AND wm.status != 'Read' THEN 1 ELSE 0 END) as unread_count,
			c.first_name,
			c.last_name,
			c.full_name
		FROM `tabWhatsApp Message` wm
		LEFT JOIN `tabContact` c ON wm.contact = c.name
		GROUP BY
			CASE WHEN wm.type = 'Incoming' THEN wm.`from` ELSE wm.`to` END,
			wm.link_to,
			wm.link_name
		ORDER BY MAX(wm.creation) DESC
	""", as_dict=1)

	# Process contact display names
	for chat in chats:
		if chat.get('full_name'):
			chat['contact_display'] = chat['full_name']
		elif chat.get('first_name'):
			last_name = (chat.get('last_name') or '').strip()
			chat['contact_display'] = f"{chat['first_name']} {last_name}".strip()
		elif chat.get('contact'):
			chat['contact_display'] = chat['contact']
		else:
			chat['contact_display'] = chat.get('contact_number') or 'Unknown'

		chat.pop('first_name', None)
		chat.pop('last_name', None)
		chat.pop('full_name', None)

		if chat.get('last_activity'):
			chat['last_activity_formatted'] = frappe.utils.pretty_date(chat['last_activity'])

	return chats

@frappe.whitelist()
def get_messages(contact_number, party_type=None, party=None):
	"""Fetch all messages for a conversation with a given contact number (either direction)."""
	party_filter = ""
	args = [contact_number, contact_number]
	if party_type and party:
		party_filter = "AND link_to = %s AND link_name = %s"
		args += [party_type, party]

	messages = frappe.db.sql(f"""
		SELECT
			name,
			message as content,
			type,
			creation,
			`to`,
			`from`,
			link_to as party_type,
			link_name as party,
			status
		FROM `tabWhatsApp Message`
		WHERE (`from` = %s OR `to` = %s)
		{party_filter}
		ORDER BY creation ASC
	""", tuple(args), as_dict=1)

	# Mark all incoming unread as read
	frappe.db.sql("""
		UPDATE `tabWhatsApp Message` SET status = 'Read'
		WHERE `from` = %s AND type = 'Incoming' AND status != 'Read'
	""", (contact_number,))

	contact_name = frappe.db.get_value("Contact", {"mobile_no": contact_number}, "full_name")

	for msg in messages:
		if msg["type"] == "Outgoing":
			msg["direction"] = "sent"
		else:
			msg["direction"] = "received"
		msg["contact_display"] = contact_name or contact_number

	return messages

@frappe.whitelist()
def send_message(contact, content, party_type=None, party=None):
	settings = frappe.get_doc("WhatsApp Settings", "WhatsApp Settings")
	business_number = settings.get("phone_id") or ""

	new_message = frappe.get_doc({
		"doctype": "WhatsApp Message",
		"type": "Outgoing",
		"from": business_number,
		"to": contact,
		"message": content,
		"content_type": "text",
		"message_type": "Manual",
		"link_to": party_type or "",
		"link_name": party or "",
	})
	new_message.insert()
	return new_message.name
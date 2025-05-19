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
	# Show only unique contacts/parties with their latest message and unread count
	chats = frappe.db.sql("""
		SELECT 
			contact, 
			link_to as party_type,
			link_name as party,
			MAX(name) as chat_id,
			MAX(message) as last_message,
			SUM(CASE WHEN type = 'Incoming' AND status != 'Read' THEN 1 ELSE 0 END) as unread_count
		FROM (
			SELECT 
				CASE 
					WHEN type = 'Outgoing' THEN `to`
					ELSE `from`
				END as contact,
				link_to,
				link_name,
				name,
				message,
				creation,
				type,
				status
			FROM `tabWhatsApp Message`
		) as sub
		GROUP BY contact, link_to, link_name
		ORDER BY MAX(creation) DESC
	""", as_dict=1)
	return chats

@frappe.whitelist()
def get_messages(contact, party_type=None, party=None):
	# Fetch all messages for this contact/party
	filters = [
		["to", "=", contact],
		["from", "=", contact, "or"]
	]
	if party_type and party:
		filters.append(["link_to", "=", party_type])
		filters.append(["link_name", "=", party])
	messages = frappe.db.sql("""
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
		WHERE (`to` = %s OR `from` = %s)
		{party_filter}
		ORDER BY creation ASC
	""".format(
		party_filter="AND link_to = %s AND link_name = %s" if party_type and party else ""
	), ([contact, contact] + ([party_type, party] if party_type and party else [])), as_dict=1)
	# Mark all incoming unread as read
	frappe.db.sql("""
		UPDATE `tabWhatsApp Message` SET status = 'Read'
		WHERE `from` = %s AND status != 'Read'
	""", (contact,))
	for msg in messages:
		if msg["type"] == "Outgoing" and msg["to"] == contact:
			msg["direction"] = "sent"
		else:
			msg["direction"] = "received"
		msg["contact_name"] = contact
	return messages

@frappe.whitelist()
def send_message(contact, content):
	# Create new outgoing message to the contact
	new_message = frappe.get_doc({
		"doctype": "WhatsApp Message",
		"type": "Outgoing",
		"to": contact,
		"message": content,
		"content_type": "text",
		"message_type": "Manual"
	})
	new_message.insert()
	return new_message.name
 
	
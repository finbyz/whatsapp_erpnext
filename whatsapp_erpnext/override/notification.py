# Copyright (c) 2018, Frappe Technologies and contributors
# License: MIT. See LICENSE

import json
import os
from collections import namedtuple
import frappe
from frappe.utils import nowdate,add_days, add_months, add_years
from frappe.utils.safe_exec import get_safe_globals
from frappe.desk.form import assign_to
from jinja2 import Template
try:
	from productivity_next.productivity_next.override_doctype_class.notification import Notification as _Notification
except ImportError:
	from frappe.email.doctype.notification.notification import Notification as _Notification
from frappe.email.doctype.notification.notification import get_context
from whatsapp_erpnext.whatsapp_erpnext.doc_events.notification import send_template_message



class Notification(_Notification):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.
    
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.email.doctype.notification_recipient.notification_recipient import NotificationRecipient
		from frappe.types import DF

		attach_print: DF.Check
		channel: DF.Literal["Email", "Slack", "System Notification", "SMS","WhatsApp","Task"]
		condition: DF.Code | None
		date_changed: DF.Literal[None]
		days_in_advance: DF.Int
		document_type: DF.Link
		enabled: DF.Check
		event: DF.Literal[
			"",
			"New",
			"Save",
			"Submit",
			"Cancel",
			"Days After",
			"Days Before",
			"Value Change",
			"Method",
			"Custom",
		]
		is_standard: DF.Check
		message: DF.Code | None
		message_type: DF.Literal["Markdown", "HTML", "Plain Text"]
		method: DF.Data | None
		module: DF.Link | None
		print_format: DF.Link | None
		property_value: DF.Data | None
		recipients: DF.Table[NotificationRecipient]
		send_system_notification: DF.Check
		send_to_all_assignees: DF.Check
		sender: DF.Link | None
		sender_email: DF.Data | None
		set_property_after_alert: DF.Literal[None]
		slack_webhook_url: DF.Link | None
		subject: DF.Data | None
		value_changed: DF.Literal[None]
	# end: auto-generated types
   
	def send(self, doc):
		"""Build recipients and send Notification"""

		context = get_context(doc)
		context = {"doc": doc, "alert": self, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))

		if self.is_standard:
			self.load_standard_properties(context)
		try:
			if self.channel == "Email":
				self.send_an_email(doc, context)

			if self.channel == "Slack":
				self.send_a_slack_msg(doc, context)

			if self.channel == "SMS":
				self.send_sms(doc, context)

			if self.channel == "System Notification" or self.send_system_notification:
				self.create_system_notification(doc, context)
			
			if self.channel == "WhatsApp":
				send_template_message(self,doc)
    
			if self.channel == "Task":
				self.create_task(doc, context)
		except Exception:
			self.log_error("Failed to send Notification")
	
	def validate(self):
		super().validate()

		if not hasattr(_Notification, 'create_task') and self.channel == "Task":
			frappe.throw("Task Notification is not supported without Productivity Next")

	def create_task(self, doc, context):
		if hasattr(_Notification, 'create_task'):
			return super().create_task(doc, context)
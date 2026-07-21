// Copyright (c) 2023, Finbyz Tech Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('WhatsApp Message', {
	refresh: function(frm) {
		if (frm.doc.type == 'Incoming'){
			frm.add_custom_button(__("Reply"), function(){
				frappe.new_doc("WhatsApp Message", {"to": frm.doc.from});

			});
		}
		if (frm.doc.status == "Failed"){
			frm.add_custom_button(__("Retry"), function(){
				frappe.call({
					method: "whatsapp_erpnext.whatsapp_erpnext.doc_events.notification.retry_message",
					args: {
						whatsapp_msg_id: frm.doc.name
					},
					
					callback: function(r){
						if (r.message){
							frappe.msgprint(r.message);
							frm.reload_doc();
						}
					}
				});
			});
		}
	}
});

frappe.ui.form.on('Purchase Order', {
    onload: function(frm){
        let fields = [
			{
				label: __("Select Notification"),
				fieldtype:'Link',
				fieldname: 'notification',
                options: "Notification",
                filters: {
                    "channel": "WhatsApp",
                    "document_type": frm.doc.doctype
                },
                reqd: 1
			},
            {
				label: __("Mobile No"),
				fieldtype:'Data',
				fieldname: 'mobile_no',
				options: "Phone",
				default: frm.doc.contact_mobile,
				reqd: 1
			}
		];
        if (!frm.custom_buttons || !frm.custom_buttons['Send WhatsApp Message']) {
            frm.page.add_menu_item(
                __("Send WhatsApp Message"),
                () => {
                    frm.dialog = new frappe.ui.Dialog({
                        title: __("Send WhatsApp Message"),
                        fields: fields
                    });
                    frm.dialog.set_primary_action(__("Send Message"), function() {
                        let values = frm.dialog.get_values();
                        if (!values) return;
                        frappe.call({ 
                            method: 'whatsapp_erpnext.whatsapp_erpnext.doc_events.notification.send_notification',
                            args: {
                                "notification": values.notification,
                                "ref_doctype": frm.doc.doctype,
                                "ref_docname": frm.doc.name,
                                "mobile_no": values.mobile_no
                            },
                            callback: (r) => {
                                if (r.message) {
                                    frappe.msgprint(__("Message sent successfully"));
                                }
                                frm.dialog.hide();
                            },
                            freeze: true,
                            freeze_message: __("Sending WhatsApp message...")
                        });
                    });
                    frm.dialog.show();
                }
            );
        }
    }
})
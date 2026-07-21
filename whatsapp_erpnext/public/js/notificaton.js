frappe.ui.form.on("Notification", {
    channel: function (frm) {
        if(frm.doc.channel == "WhatsApp"){
            frm.doc.message = null
        }
    },
    refresh: function (frm) {
        let get_select_options = function (df, parent_field) {
            // Append parent_field name along with fieldname for child table fields
            let select_value = parent_field ? df.fieldname + "," + parent_field : df.fieldname;

            return {
                value: select_value,
                label: df.label + " (" + __(df.fieldname) + ")",
            };
        };
        let receiver_fields = [];
        let fields = frappe.get_doc("DocType", frm.doc.document_type).fields;

        receiver_fields = $.map(fields, function (d) {
            return ["Currency", "Data", "Datetime", "Date", "Duration", "Dynamic Link", "Float", "Int", "Json", "Link", "Long Text", "Percent", "Phone", "Read Only", "Select", "Small Text", "Text", "Time"].includes(d.fieldtype) ? get_select_options(d) : null;
        });
        frm.fields_dict.fields.grid.update_docfield_property(
            "field_name",
            "options",
            [""].concat("name").concat(receiver_fields)
        );
    }
})
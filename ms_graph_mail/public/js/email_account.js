frappe.ui.form.on("Email Account", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.ms_graph_send || !frm.doc.enable_outgoing) return;

		frm.add_custom_button(__("Send Test via Microsoft Graph"), () => {
			frappe.prompt(
				{
					fieldname: "recipient",
					fieldtype: "Data",
					options: "Email",
					label: __("Send to"),
					reqd: 1,
					default: frappe.session.user_email,
				},
				(values) => {
					frappe
						.call({
							method: "ms_graph_mail.graph.send_test_email",
							args: { email_account: frm.doc.name, recipient: values.recipient },
							freeze: true,
							freeze_message: __("Sending..."),
						})
						.then((r) => r.message && frappe.msgprint(r.message, __("Microsoft Graph")));
				},
				__("Microsoft Graph test"),
				__("Send")
			);
		});
	},
});

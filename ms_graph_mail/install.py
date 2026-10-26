import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Email Account": [
		{
			"fieldname": "ms_graph_send",
			"label": "Send via Microsoft Graph",
			"fieldtype": "Check",
			"insert_after": "connected_user",
			"depends_on": 'eval:doc.auth_method === "OAuth"',
			"description": "Send outgoing mail through the Microsoft Graph API (application permission "
			"Mail.Send on the Connected App) instead of SMTP. Use it when SMTP AUTH is disabled in "
			"Microsoft 365.",
		}
	]
}


def after_install():
	create_custom_fields(CUSTOM_FIELDS, update=True)


def before_uninstall():
	for doctype, fields in CUSTOM_FIELDS.items():
		for field in fields:
			name = frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]})
			if name:
				frappe.delete_doc("Custom Field", name, ignore_permissions=True)

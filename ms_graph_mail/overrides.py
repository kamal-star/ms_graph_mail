import frappe
from frappe import _
from frappe.email.doctype.email_account.email_account import EmailAccount

from ms_graph_mail.graph import get_app_token


class GraphEmailAccount(EmailAccount):
	def validate_smtp_conn(self):
		# A Graph account never logs in to SMTP (which may be switched off in the
		# tenant), so prove instead that the app can get a Graph token.
		if self.get("ms_graph_send"):
			if not self.connected_app:
				frappe.throw(_("Set a Connected App to send via Microsoft Graph."))
			get_app_token(self.connected_app, refresh=True)
			return
		super().validate_smtp_conn()

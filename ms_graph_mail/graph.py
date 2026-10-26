"""Send ERPNext's outgoing email through Microsoft Graph instead of SMTP.

For Microsoft 365 tenants where SMTP AUTH is switched off (for example by
security defaults). Frappe passes every queued email to `send` through the
`override_email_send` hook. Accounts with "Send via Microsoft Graph" go out
through Graph's sendMail; every other account still uses SMTP as before.

Graph is called with an app-only token (client credentials) from the Email
Account's Connected App, so the app registration needs the Microsoft Graph
*application* permission Mail.Send with admin consent.
"""

import base64
from urllib.parse import quote

import frappe
import requests
from frappe import _

from ms_graph_mail.delivery import norm, plan

GRAPH_SCOPE = "https://graph.microsoft.com/.default"
SEND_URL = "https://graph.microsoft.com/v1.0/users/{mailbox}/sendMail"
TIMEOUT = 60


def uses_graph(email_account) -> bool:
	return bool(email_account and email_account.get("ms_graph_send") and email_account.get("connected_app"))


def _cache():
	return frappe.cache() if callable(frappe.cache) else frappe.cache


def _token_key(connected_app):
	return f"ms_graph_mail:token:{connected_app}"


def get_app_token(connected_app: str, refresh: bool = False) -> str:
	"""App-only Graph token, cached until five minutes before it expires."""
	if not refresh:
		token = _cache().get_value(_token_key(connected_app))
		if token:
			return token

	app = frappe.get_doc("Connected App", connected_app)
	if not app.token_uri:
		frappe.throw(_("Connected App {0} has no Token URI.").format(connected_app))

	response = requests.post(
		app.token_uri,
		data={
			"grant_type": "client_credentials",
			"client_id": app.client_id,
			"client_secret": app.get_password("client_secret", raise_exception=False) or "",
			"scope": GRAPH_SCOPE,
		},
		timeout=TIMEOUT,
	)
	data = _json(response)
	if response.status_code != 200 or not data.get("access_token"):
		frappe.throw(
			_("Microsoft Graph sign-in failed: {0}").format(data.get("error_description") or response.text[:500]),
			title=_("Microsoft Graph"),
		)

	expires = max(int(data.get("expires_in") or 3600) - 300, 60)
	_cache().set_value(_token_key(connected_app), data["access_token"], expires_in_sec=expires)
	return data["access_token"]


def send(queue_doc, sender, recipient, message):
	"""`override_email_send` hook, called once per pending recipient of an Email Queue."""
	account = queue_doc.get_email_account(raise_error=True)
	raw = message if isinstance(message, bytes) else (message or "").encode()

	if not uses_graph(account):
		_send_smtp(account, sender, recipient, raw)
		return

	if frappe.flags.in_test and not frappe.flags.testing_email:
		return

	pending = {norm(r.recipient) for r in queue_doc.recipients if not r.is_mail_sent()}
	mime, delivered = plan(raw, recipient, pending, account.email_id)
	post_mime(account.connected_app, account.email_id, mime)

	# Frappe marks `recipient` itself; the others this send reached are marked here
	# so the loop skips them instead of sending them a second copy.
	me = norm(recipient)
	for r in queue_doc.recipients:
		if norm(r.recipient) in delivered and norm(r.recipient) != me and not r.is_mail_sent():
			r.status = "Sent"
			r.update_db(status="Sent", commit=True)


def post_mime(connected_app: str, mailbox: str, mime: bytes):
	url = SEND_URL.format(mailbox=quote(mailbox))
	body = base64.b64encode(mime)
	for attempt in (1, 2):
		token = get_app_token(connected_app, refresh=attempt == 2)
		response = requests.post(
			url,
			data=body,
			headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
			timeout=TIMEOUT,
		)
		if response.status_code == 202:
			return
		if response.status_code == 401 and attempt == 1:
			continue
		break

	error = _json(response).get("error") or {}
	frappe.throw(
		_("Microsoft Graph could not send the email ({0}): {1}").format(
			response.status_code, error.get("message") or response.text[:500]
		),
		title=_("Microsoft Graph"),
	)


def _send_smtp(account, sender, recipient, raw: bytes):
	"""What Frappe does when no override is installed."""
	if frappe.flags.in_test and not frappe.flags.testing_email:
		return
	account.get_smtp_server().session.sendmail(
		from_addr=sender, to_addrs=recipient, msg=raw.decode("utf-8").encode()
	)


def _json(response):
	try:
		return response.json()
	except ValueError:
		return {}


@frappe.whitelist()
def send_test_email(email_account: str, recipient: str):
	"""Send a test email through the account right now and report the result."""
	frappe.only_for("System Manager")
	account = frappe.get_doc("Email Account", email_account)
	if not uses_graph(account):
		frappe.throw(_("Tick 'Send via Microsoft Graph' and set a Connected App on {0} first.").format(email_account))

	frappe.sendmail(
		recipients=[recipient],
		sender=account.email_id,
		subject=_("ERPNext test email via Microsoft Graph"),
		message=_("This test email was sent by ERPNext from {0} through the Microsoft Graph API.").format(
			account.email_id
		),
		now=True,
	)

	queue = frappe.get_all(
		"Email Queue",
		filters={"sender": ["like", f"%{account.email_id}%"]},
		fields=["name", "status", "error"],
		order_by="creation desc",
		limit=1,
	)
	if queue and queue[0].status == "Sent":
		return _("Sent to {0}. Check that inbox (and the Sent Items of {1}).").format(recipient, account.email_id)
	error = (queue[0].error or "").strip().splitlines()[-1] if queue and queue[0].error else ""
	frappe.throw(
		_("Not sent ({0}). {1}").format(queue[0].status if queue else _("not queued"), error),
		title=_("Microsoft Graph"),
	)

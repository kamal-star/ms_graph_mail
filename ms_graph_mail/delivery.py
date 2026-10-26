"""Who a Graph send should reach, and the message headers that make it so.

Kept free of Frappe so it can be tested on its own.

Frappe builds one MIME message per recipient: To holds that recipient (or every
To address when recipients are exposed in the header) and CC lists all CC
addresses. Over SMTP it then sends each copy to just that one envelope address.
Graph has no separate envelope; it delivers to every address in To / CC / BCC.
So each send is narrowed to the addresses still waiting, and the caller marks
everyone it reached as sent. Each person then gets exactly one copy, and CC
stays visible on the message that carries it.
"""

from email import policy
from email.parser import BytesParser
from email.utils import formataddr, getaddresses, parseaddr

POLICY = policy.SMTP.clone(refold_source="none")


def norm(address: str) -> str:
	return (address or "").strip().lower()


def _addresses(msg, header):
	return [(name, addr) for name, addr in getaddresses(msg.get_all(header, [])) if addr]


def _set(msg, header, addresses):
	del msg[header]
	if addresses:
		msg[header] = ", ".join(formataddr(a) for a in addresses)


def plan(message: bytes, recipient: str, pending: set[str], mailbox: str):
	"""Return (mime_bytes, delivered) for one Graph send.

	message   the MIME Frappe built for `recipient`
	pending   lower-cased addresses of this queue's recipients not yet sent
	mailbox   the sending mailbox (the Email Account's address)
	delivered lower-cased addresses this send reaches
	"""
	msg = BytesParser(policy=POLICY).parsebytes(message)
	me = norm(recipient)

	to = [a for a in _addresses(msg, "To") if norm(a[1]) in pending]
	cc = [a for a in _addresses(msg, "Cc") if norm(a[1]) in pending]
	reached = {norm(a[1]) for a in to + cc}
	if me not in reached:
		# A BCC recipient, or a To recipient Frappe left out of an exposed header:
		# they get their own copy.
		to, cc = [("", recipient)], []
	elif not to:
		to, cc = cc, []

	_set(msg, "To", to)
	_set(msg, "Cc", cc)
	del msg["Bcc"]

	# Graph only sends as the mailbox it is called for. Keep the display name, and
	# keep the original sender reachable through Reply-To.
	from_name, from_addr = parseaddr(str(msg.get("From", "")))
	if norm(from_addr) != norm(mailbox):
		if not msg.get("Reply-To") and from_addr:
			msg["Reply-To"] = formataddr((from_name, from_addr))
		del msg["From"]
		msg["From"] = formataddr((from_name, mailbox))

	return msg.as_bytes(policy=POLICY), {norm(a[1]) for a in to + cc}

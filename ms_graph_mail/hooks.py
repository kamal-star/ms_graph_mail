app_name = "ms_graph_mail"
app_title = "MS Graph Mail"
app_publisher = "MachineSens IoT"
app_description = "Send Frappe / ERPNext email through the Microsoft Graph API instead of SMTP"
app_email = "info@machinesensiot.com"
app_license = "mit"

# Every queued email passes through ms_graph_mail.graph.send. Accounts with
# "Send via Microsoft Graph" go out through Graph; all others use SMTP as before.
override_email_send = "ms_graph_mail.graph.send"

# Saving a Graph account checks a Graph token instead of logging in to SMTP.
override_doctype_class = {
	"Email Account": "ms_graph_mail.overrides.GraphEmailAccount",
}

doctype_js = {
	"Email Account": "public/js/email_account.js",
}

after_install = "ms_graph_mail.install.after_install"
after_migrate = "ms_graph_mail.install.after_install"
before_uninstall = "ms_graph_mail.install.before_uninstall"

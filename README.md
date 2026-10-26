## MS Graph Mail

Sends Frappe / ERPNext email through the **Microsoft Graph API** instead of SMTP.

Use it when a Microsoft 365 tenant blocks SMTP sending. This shows up as
`5.7.139 Authentication unsuccessful, SmtpClientAuthentication is disabled for the Tenant`,
for example when **Security defaults** are on. Graph's `sendMail` isn't affected by
that setting, needs no paid plan, and only uses HTTPS (no port 25 / 587).

- Only Email Accounts with **Send via Microsoft Graph** ticked use Graph. Every other
  account keeps sending over SMTP exactly as before.
- Mail goes out **from the account's mailbox** and is saved in its Sent Items.
- To and CC work like normal email. Each person receives one copy and CC stays
  visible; BCC recipients get their own copy.
- Incoming mail is unchanged (IMAP with the account's OAuth sign-in).
- Works on Frappe / ERPNext v15 and v16.

### Microsoft 365 side (once)

In the Entra **App registration** used by the Email Account's Connected App:

1. **API permissions → Add → Microsoft Graph → Application permissions → `Mail.Send`**
2. **Grant admin consent**

`Mail.Send` as an application permission can send from any mailbox in the tenant. To
limit it to the ERPNext mailbox, an Exchange admin can scope it in Exchange Online
PowerShell (no extra licence needed):

```powershell
New-DistributionGroup -Name "ERPNext Graph Senders" -Type Security -Members info@example.com
New-ApplicationAccessPolicy -AppId <client-id> -PolicyScopeGroupId "ERPNext Graph Senders" -AccessRight RestrictAccess -Description "ERPNext may send only as these mailboxes"
```

### Install

```bash
cd ~/frappe-bench
bench get-app https://github.com/kamal-star/ms_graph_mail
bench --site <your-site> install-app ms_graph_mail
bench build --app ms_graph_mail
bench --site <your-site> clear-cache
sudo supervisorctl restart all        # or `bench restart`
```

### Set up the Email Account

1. The account uses **Authentication Method: OAuth** with its **Connected App**, and has
   been authorised (**Authorize API Access**). The Connected App holds the Client ID and
   Client Secret of the app registration above.
2. Tick **Send via Microsoft Graph** (it appears under Connected User).
3. Tick **Enable Outgoing** (and **Default Outgoing** if it should be the default) and save.
   Saving checks that a Graph token can be obtained instead of trying an SMTP login.
4. Click **Send Test via Microsoft Graph** at the top of the form to send a test email.

### Troubleshooting

| Message | Cause |
| --- | --- |
| `Microsoft Graph sign-in failed: AADSTS7000215 …` | Wrong or expired client secret in the Connected App |
| `… (403): Access is denied` / `ErrorAccessDenied` | `Mail.Send` application permission missing, admin consent not granted, or blocked by an Application Access Policy |
| `… (404) … mailbox` | The account's email address isn't a mailbox in the tenant |
| `… (413)` | The email with attachments is over Graph's 4 MB request limit |

Failed sends stay in **Email Queue** with the error, and are retried like any other email.

#### License

MIT

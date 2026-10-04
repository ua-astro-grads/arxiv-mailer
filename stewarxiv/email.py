"""Steps 3-4: render the mailing from the Jinja2 templates, then compose and send it."""
import os
import smtplib
import ssl
from email.message import EmailMessage

import jinja2

# mail settings (config.py, copied from config.py.template)
import config

# https://stackoverflow.com/questions/33857698/sending-email-from-python-using-starttls
_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)

env = jinja2.Environment(
    # the templates live in the repo root, one level above this package
    loader=jinja2.FileSystemLoader(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

def render_mailing(context_dict):
    html_template = env.get_template('mailing.jinja2.html')
    html_mailing = html_template.render(**context_dict)
    text_template = env.get_template('mailing.jinja2.txt')
    text_mailing = text_template.render(**context_dict)

    return html_mailing, text_mailing

def compose_email(from_address, to_addresses, subject, html_mailing, text_mailing,
    cc_addresses=None, thumbnails=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_addresses
    if cc_addresses:
        msg['CC'] = cc_addresses
    msg.set_content(text_mailing)
    msg.add_alternative(html_mailing, subtype='html')
    # attach headshots inline (multipart/related) so the html can show them
    # with src="cid:..." without fetching anything remotely
    html_part = msg.get_payload()[1]
    for cid, png in (thumbnails or {}).items():
        html_part.add_related(png, 'image', 'png', cid=f'<{cid}>')
    return msg

def send_email(msg):
    host = config.MAIL_SERVER
    port = int(config.MAIL_PORT)
    user = config.MAIL_USERNAME
    password = config.MAIL_PASSWORD

    # only TLSv1 or higher
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3

    context.set_ciphers(_DEFAULT_CIPHERS)
    context.set_default_verify_paths()
    context.verify_mode = ssl.CERT_REQUIRED
    smtp_server = smtplib.SMTP_SSL(host, port=port, context=context)
    smtp_server.login(user, password)
    smtp_server.send_message(msg)

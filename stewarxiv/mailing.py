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
    # the templates live in templates/ in the repo root, next to this package
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

def render_mailing(context_dict):
    """Render the HTML and plain-text versions of the mailing.

    Fills templates/mailing.jinja2.html (which includes author.jinja2.html
    for each author) and templates/mailing.jinja2.txt with the context.

    Args:
        context_dict: Template variables: people, posts, all_authors,
            run_time and day_of_week.

    Returns:
        tuple[str, str]: (html, text).
    """
    html_template = env.get_template('mailing.jinja2.html')
    html_mailing = html_template.render(**context_dict)
    text_template = env.get_template('mailing.jinja2.txt')
    text_mailing = text_template.render(**context_dict)

    return html_mailing, text_mailing

def compose_email(from_address, to_addresses, subject, html_mailing, text_mailing,
    cc_addresses=None, thumbnails=None):
    """Build the email message.

    Sets the headers, adds the plain-text body with the HTML as an
    alternative version, and attaches each thumbnail to the HTML part as an
    inline image (multipart/related) under its content ID, so the HTML shows
    it with src="cid:..." without loading anything from the web.

    Args:
        from_address: Sender, as an email.headerregistry.Address.
        to_addresses: Recipient Address, or a list of them.
        subject: Subject line.
        html_mailing: HTML body from render_mailing.
        text_mailing: Plain-text body from render_mailing.
        cc_addresses: Optional CC Address, or a list of them.
        thumbnails: Optional {content ID: PNG bytes} from build_thumbnails.

    Returns:
        email.message.EmailMessage: The message, ready for send_email.
    """
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
    """Send a message through the SMTP server set in config.py.

    Opens an SSL connection to config.MAIL_SERVER:MAIL_PORT (no SSLv2/v3,
    certificate verification on, ciphers from _DEFAULT_CIPHERS), logs in with
    MAIL_USERNAME and MAIL_PASSWORD, and sends the message to the addresses
    in its To and CC headers.

    Args:
        msg: The message from compose_email.
    """
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

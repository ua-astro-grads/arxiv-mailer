#!/usr/bin/env python
"""Entry point: build the directory, find today's matching postings, and email them.

The pipeline steps live in the stewarxiv/ package; see the README for a map.
"""
import argparse
import datetime
import os
import os.path
import pickle
import logging
import sys
import base64
from email.headerregistry import Address

from dateutil import tz

from stewarxiv.directory import build_directory
from stewarxiv.feed import fetch_feed, feed_is_fresh, get_matching_posts
from stewarxiv.names import Author
from stewarxiv.thumbnails import build_thumbnails
from stewarxiv.email import render_mailing, compose_email, send_email

# mail settings (config.py, copied from config.py.template)
import config

log = logging.getLogger(__name__)

HERE = os.path.dirname(__file__)

def main():
    run_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    tzmst = tz.gettz('America/Phoenix')
    run_time_local = run_time.astimezone(tzmst)
    day_of_week = run_time_local.strftime('%A')

    parser = argparse.ArgumentParser(description="Email today's astro-ph postings by UofA people.")
    parser.add_argument('-d', '--demo', action='store_true',
        help="demo mode: skip the affiliation check, reuse/save demo.pickle, write "
             "mailing.html/.txt/.eml, and send only to the admin address")
    args = parser.parse_args()
    demo_mode = args.demo
    if demo_mode and os.path.exists('./demo.pickle'):
        with open('./demo.pickle', 'rb') as f:
            context = pickle.load(f)
            # define locals from pickle
            people = context['people']
            posts = context['posts']
            all_authors = context['all_authors']
            # pickles saved before Author existed store each author as a
            # plain (name, (key, score)) tuple
            for post in posts:
                post['authors'] = [a if isinstance(a, Author) else Author(a[0], *a[1])
                                   for a in post['authors']]
            # except run_time, update that in loaded dict
            context['run_time'] = run_time_local.strftime('%Y-%m-%d %H:%M %Z')
            context['day_of_week'] = day_of_week
    else:
        people = build_directory()
        feed = fetch_feed()
        if not feed_is_fresh(feed):
            sys.exit(1)
        posts, all_authors = get_matching_posts(feed, people, check_affiliation=not demo_mode)
        context = {
            'people': people,
            'posts': posts,
            'all_authors': all_authors,
            'run_time': run_time_local.strftime('%Y-%m-%d %H:%M %Z'),
            'day_of_week': day_of_week,
        }
        if demo_mode:
            with open('./demo.pickle', 'wb') as f:
                pickle.dump(context, f)

    thumbnails = build_thumbnails(all_authors)
    html_mailing, text_mailing = render_mailing(context)
    if demo_mode:
        # browsers can't resolve cid: links, so inline the images for preview
        preview_html = html_mailing
        for cid, png in thumbnails.items():
            data_uri = 'data:image/png;base64,' + base64.b64encode(png).decode()
            preview_html = preview_html.replace(f'cid:{cid}', data_uri)
        with open(os.path.join(HERE, 'mailing.html'), 'w') as f:
            f.write(preview_html)
        with open(os.path.join(HERE, 'mailing.txt'), 'w') as f:
            f.write(text_mailing)

    # Compose the email
    from_addr_spec = config.MAIL_USERNAME if not demo_mode else 'stewarxiv@gmail.com'
    from_addr = Address("StewarXiv", addr_spec=from_addr_spec)
    # decide who to send to depending on content or demoing
    if not demo_mode and len(posts) > 0:
        to_addrs = [Address("StewarXiv", addr_spec=config.MAIL_SENDTO)]
    else:
        to_addrs = [Address("ADMIN", addr_spec=config.MAIL_USERNAME)]
    subject = f'{day_of_week}\'s update: {len(posts)} {"preprint" if len(posts) == 1 else "preprints"} from {len(all_authors)} {"colleague" if len(all_authors) == 1 else "colleagues"}'
    # Compose the email (also CC the sender of the email)
    msg = compose_email(from_addr, to_addrs, subject, html_mailing, text_mailing,
        cc_addresses=from_addr, thumbnails=thumbnails)
    if demo_mode:
        with open('mailing.eml', 'wb') as f:
            f.write(bytes(msg))
    # Send the email
    send_email(msg)

if __name__ == "__main__":
    logging.basicConfig(level='WARN')
    log.setLevel('DEBUG')
    # Set up a file to write the log
    fh = logging.FileHandler(os.path.join(HERE, f'logs/{datetime.date.today()}.log'))
    fh.setLevel('DEBUG')
    log.addHandler(fh)
    # the pipeline steps log under 'stewarxiv.*'; send those to the same places
    pkg_log = logging.getLogger('stewarxiv')
    pkg_log.setLevel('DEBUG')
    pkg_log.addHandler(fh)
    main()

#!/usr/bin/env python
import datetime
import os
import os.path
import pickle
import re
import logging
import sys
import unicodedata
import smtplib
import ssl
# https://stackoverflow.com/questions/33857698/sending-email-from-python-using-starttls
_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)
from dateutil.parser import parse
from dateutil import tz
from bs4 import BeautifulSoup
import feedparser
import jinja2
import requests
import tarfile
import io

log = logging.getLogger(__name__)
DEMO_MODE = False

HERE = os.path.dirname(__file__)

def soupify(url):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        req = requests.get(url, verify=False)
    return BeautifulSoup(req.text, features="lxml")

FACULTY = 1
POSTDOC = 2
STUDENT = 3


def gather_affiliation_evidence(arxiv_id):
    url = f'https://arxiv.org/e-print/{arxiv_id}'
    evidence = 0
    try:
        res = requests.get(url)
        buff = io.BytesIO(res.content)
        archive = tarfile.open(fileobj=buff)
        texfiles = [m for m in archive.getmembers() if m.name.lower().endswith('.tex')]

        UOFA_RE = re.compile(r'(university of arizona|steward observatory|arizona\.edu|lbto\.org|gmto\.org)', flags=re.IGNORECASE)

        for info in texfiles:
            fh = archive.extractfile(info)
            contents = fh.read().decode('utf8')
            matches = UOFA_RE.findall(contents)
            evidence += len(matches)
    except Exception as e:
        log.debug(e)
    return evidence


def normalize_caseless(text):
    text = re.sub(r'[^\w]', ' ', text)
    # thanks to https://stackoverflow.com/a/29247821
    text = unicodedata.normalize("NFKD", text.casefold())
    text = text.strip()
    return text

def build_directory():
    people = {}
    base_link = 'https://astro.arizona.edu'

    faculty_page = soupify('https://astro.arizona.edu/people/all-faculty')
    for facwrap in faculty_page.select('.card-body'):
        name = tuple(filter(None, facwrap.select_one('h1').text.split('\n')))
        name = tuple(normalize_caseless(part.strip()) for part in name)[::-1] # lower case and reverse order

        # retrieve link to individual page
        ind_page_link = facwrap.find_all('a', href=True)[0]['href']
        ind_page = soupify(base_link + ind_page_link)

        # get position
        position = ind_page.find_all("div", class_="field--name-field-az-titles")[0].text.replace('\n', '')
        # get image
        image = base_link + ind_page.select('article')[0].select_one('img')['src']

        people[name]= {
            'role': FACULTY,
            'position': position,
            'image': image, 
        }

    postdoc_page = soupify('https://astro.arizona.edu/people/postdocs')
    for wrap in postdoc_page.select('.card-body'):
        name = tuple(wrap.select('h3')[0].text.replace('\n', '').split(' ', 1))
        name = tuple(normalize_caseless(part.strip()) for part in name)[::-1] # lower case and reverse order

        # retrieve link to individual page
        ind_page_link = wrap.find_all('a', href=True)[0]['href']
        ind_page = soupify(base_link + ind_page_link)

        # get position
        try:
            position = ind_page.find_all("div", class_="field--name-field-az-titles")[0].text.replace('\n', '')
        except:
            continue
        
        # get image
        image = base_link + ind_page.select('article')[0].select_one('img')['src']

        people[name]= {
            'role': POSTDOC,
            'position': position,
            'image': image,
        }

    student_page = soupify('https://astro.arizona.edu/people/graduate-students')
    for wrap in student_page.select('.card-body'):
        name = tuple(filter(None, wrap.select_one('h1').text.split('\n')))
        name = tuple(normalize_caseless(part.strip()) for part in name)[::-1] #case and reverse order

        # retrieve link to individual page
        ind_page_link = wrap.find_all('a', href=True)[0]['href']
        ind_page = soupify(base_link + ind_page_link)

        # get image
        image = None #base_link + ind_page.select('article')[0].select_one('img')['src']

        people[name]= {
            'role': STUDENT,
            'position': 'Graduate Student',
            'image': image,
        }

    return people

NAME_RE = re.compile(r'^(?P<first>(?:(?P<initial>\w).*)[\. ]+)+(?P<last>\w.*)$')
def test_name_regex():
    assert NAME_RE.match('J.Long').groupdict() == {'first': 'J.', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('Joseph D. Long').groupdict() == {'first': 'Joseph D. ', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('J. D. Long').groupdict() == {'first': 'J. D. ', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('J Long').groupdict() == {'first': 'J ', 'initial': 'J', 'last': 'Long'}
INITIAL_RE = re.compile(r'^\w(\.|\s|$)')
def test_initial_regex():
    assert INITIAL_RE.match('J. D.')
    assert not INITIAL_RE.match('Jo. D.')
    assert INITIAL_RE.match('J.D.')
    assert INITIAL_RE.match('J')
    assert INITIAL_RE.match('J D')

ALL_INITIALS_RE = re.compile(r'\b\w\.?\s')
def strip_initials(names):
    return ' '.join(ALL_INITIALS_RE.sub('', names).split())
def test_strip_initials():
    assert strip_initials('J. Long') == 'Long'

def approximate_name_lookup(name, people):
    # normalize at input boundary so comparisons are simply ==
    normalized_name = normalize_caseless(name)
    name_match = NAME_RE.match(normalized_name)
    if not name_match:
        log.warning(f"Unable to parse {normalized_name=} with regex")
        return None, 0
    parts = name_match.groupdict()
    first_names = parts['first'].strip()
    first_initial = parts['initial']
    last_name = parts['last'].strip()

    for person_last, person_first in people:
        score = 0
        if person_last == last_name:
            # last name matches, but what about first?
            if person_first == first_names:
                # easy: last name matches, first name(s) match
                score = 2
            elif first_names.startswith(person_first):
                score = 2
            elif first_names != first_initial and first_names in person_first:
                # first_names is a substring of person_first
                # does person_first match after removing initials?
                if strip_initials(first_names).startswith(person_first):
                    score = 2
            elif person_first in first_names:
                # does first_names match after removing initials?
                if strip_initials(first_names).startswith(person_first):
                    score = 2
            elif person_first[0] == first_initial[0]:
                # harder: last name matches, first initial matches
                # check if it's an initial (single letter followed by space, period, or end of string
                re_match = INITIAL_RE.match(first_names)
                if re_match:
                    score = 1
                # otherwise, same first initial, different first name, so no match
            # else: same last name, different first name, no match
        if score:
            return (person_last, person_first), score
    return None, 0

def test_approximate_name_lookup():
    people = {
        ('dave', 'a. bob c.'): None,
        ('ferris', 'edgar'): None,
        ('hausschuh', 'georgina'): None,
        ('rodrigo', 'marco navarro'): None
    }
    assert approximate_name_lookup('edgar ferris', people) == (('ferris', 'edgar'), 2)
    assert approximate_name_lookup('bob dave', people) == (('dave', 'a. bob c.'), 2)
    assert approximate_name_lookup('G. Hausschuh', people) == (('hausschuh', 'georgina'), 1)
    assert approximate_name_lookup('{M. Navarro Rodrigo}', people) == (('rodrigo', 'marco navarro'), 1)

UOFA_RE = re.compile(r'(university of arizona|steward observatory|arizona\.edu|lbto\.org|gmto\.org)', flags=re.IGNORECASE)

def evidence_in_texfile(fh):
    evidence = 0
    for line in fh:
        line = line.decode('utf8')
        if line[0] == '%':
            continue
        matches = UOFA_RE.findall(line)
        evidence += len(matches)
    return evidence


def gather_affiliation_evidence(arxiv_id):
    url = f'https://arxiv.org/e-print/{arxiv_id}'
    evidence = 0
    gather_success = False
    try:
        log.debug(f"Gathering evidence from {url}")
        res = requests.get(url)
        buff = io.BytesIO(res.content)
        archive = tarfile.open(fileobj=buff)
        texfiles = [m for m in archive.getmembers() if m.name.lower().endswith('.tex')]
        for info in texfiles:
            fh = archive.extractfile(info)
            evidence += evidence_in_texfile(fh)
        gather_success = True
        log.info(f'Found {evidence=} for {arxiv_id=}')
    except Exception as e:
        log.debug(e)
    return evidence, gather_success


def unpack_feed_entry(post, people):
    title = post.title
    arxiv_area = post.tags[0]['term']
    # New arXiv RSS feed has a comma-separated author list instead of the a tag
    author_names = [author.strip() for author in
        BeautifulSoup(post.author, features="lxml").text.split(',')]
    authors = [(name, approximate_name_lookup(name, people)) for name in author_names]
    our_people_score = sum(item[1][1] for item in authors)
    if our_people_score < 1:
        return
    else:
        log.info(f"Found {our_people_score=} from {authors=}")
    arxiv_id = post.link.rsplit('/', 1)[1]
    if not DEMO_MODE or DEMO_MODE:
        evidence, gather_success = gather_affiliation_evidence(arxiv_id)
        if gather_success and evidence == 0:
            log.debug(f'Skipping {arxiv_id=} for lack of evidence: {our_people_score=} {evidence=}')
            return  # no matches to UOFA_RE
        elif not gather_success and our_people_score < 2:
            return  # could be two partial matches
    # The summary now also contains the arXiv ID and the type of posting (e.g.
    # new, replacement) - just grab the abstract
    summary = BeautifulSoup(post.summary, features="lxml").text
    abstract = summary.split('Abstract: ')[-1]
    out = {
        'authors': authors,
        'title': title,
        'area': arxiv_area,
        'abstract': abstract.replace('\n', ' '),
        'arxiv_id': arxiv_id,
        'html_arxiv_id': post.id.rsplit(':', 1)[1],
    }
    return out

def get_matching_posts(people):
    feed = feedparser.parse('https://rss.arxiv.org/rss/astro-ph')
    posts = []
    all_authors = []
    update_day = parse(feed.feed['updated']).astimezone(datetime.timezone.utc).date()
    pub_day = parse(feed.feed['published']).astimezone(datetime.timezone.utc).date()
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if (update_day - today).days != 0:
        log.warn(f"Mailer was invoked but feed was last updated on {update_day} UTC")
        sys.exit(1)
    if (pub_day - today).days != 0:
        log.warn(f"Mailer was invoked but content in feed was last " +
                 f"published on {pub_day} UTC")
        sys.exit(1)
    for post in feed.entries:
        unpacked_post = unpack_feed_entry(post, people)
        if unpacked_post:
            posts.append(unpacked_post)
            for author in unpacked_post['authors']:
                if author[1][0] is not None:
                    key = author[1][0]
                    all_authors.append((key, people[key]))
    # sorting by the key, so by last names
    all_authors.sort()
    all_authors = [x[1] for x in all_authors]

    return posts, all_authors

env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

def render_mailing(context_dict):
    html_template = env.get_template('mailing.jinja2.html')
    html_mailing = html_template.render(**context_dict)
    text_template = env.get_template('mailing.jinja2.txt')
    text_mailing = text_template.render(**context_dict)

    return html_mailing, text_mailing

from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid

def compose_email(from_address, to_addresses, subject, html_mailing, text_mailing,
    cc_addresses=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_addresses
    if cc_addresses:
        msg['CC'] = cc_addresses
    msg.set_content(text_mailing)
    msg.add_alternative(html_mailing, subtype='html')
    if DEMO_MODE:
        with open('mailing.eml', 'wb') as f:
            f.write(bytes(msg))
    return msg

def send_email(msg):
    host = os.environ['MAIL_SERVER']
    port = int(os.environ['MAIL_PORT'])
    user = os.environ['MAIL_USERNAME']
    password = os.environ['MAIL_PASSWORD']

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

def main():
    global DEMO_MODE
    run_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    tzmst = tz.gettz('America/Phoenix')
    run_time_local = run_time.astimezone(tzmst)
    day_of_week = run_time_local.strftime('%A')

    if len(sys.argv) > 1:
        args = sys.argv[1:]
        if '-d' in args:
            DEMO_MODE = True
    if DEMO_MODE and os.path.exists('./demo.pickle'):
        with open('./demo.pickle', 'rb') as f:
            context = pickle.load(f)
            # define locals from pickle
            people = context['people']
            posts = context['posts']
            all_authors = context['all_authors']
            # except run_time, update that in loaded dict
            context['run_time'] = run_time_local.strftime('%Y-%m-%d %H:%M %Z')
            context['day_of_week'] = day_of_week
    else:
        people = build_directory()
        posts, all_authors = get_matching_posts(people)
        context = {
            'people': people,
            'posts': posts,
            'all_authors': all_authors,
            'run_time': run_time_local.strftime('%Y-%m-%d %H:%M %Z'),
            'day_of_week': day_of_week,
        }
        if DEMO_MODE:
            with open('./demo.pickle', 'wb') as f:
                pickle.dump(context, f)

    html_mailing, text_mailing = render_mailing(context)
    if DEMO_MODE:
        with open(os.path.join(HERE, 'mailing.html'), 'w') as f:
            f.write(html_mailing)
        with open(os.path.join(HERE, 'mailing.txt'), 'w') as f:
            f.write(text_mailing)

    # Compose the email
    from_addr_spec = os.environ['MAIL_USERNAME'] if not DEMO_MODE else 'astro-stewarxiv@list.arizona.edu'
    from_addr = Address("StewarXiv", addr_spec=from_addr_spec)
    to_addr_spec = os.environ['MAIL_SENDTO'] if not DEMO_MODE else 'nfranz@arizona.edu'
    to_addrs = [
        Address("StewarXiv", addr_spec=to_addr_spec)
    ]
    subject = f'{day_of_week}\'s update: {len(posts)} {"preprint" if len(posts) == 1 else "preprints"} from {len(all_authors)} {"colleague" if len(all_authors) == 1 else "colleagues"}'
    # Compose the email (also CC the sender of the email)
    msg = compose_email(from_addr, to_addrs, subject, html_mailing, text_mailing,
        cc_addresses=from_addr)
    # Send the email
    if not DEMO_MODE and len(posts) > 0:
        send_email(msg)

if __name__ == "__main__":
    logging.basicConfig(level='WARN')
    log.setLevel('DEBUG')
    # Set up a file to write the log
    fh = logging.FileHandler(os.path.join(HERE, f'logs/{datetime.date.today()}.log'))
    fh.setLevel('DEBUG')
    log.addHandler(fh)
    main()

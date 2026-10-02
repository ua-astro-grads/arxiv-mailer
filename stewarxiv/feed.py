"""Step 2: fetch the astro-ph RSS feed and keep postings by our people."""
import datetime
import logging
import sys

import feedparser
from bs4 import BeautifulSoup
from dateutil.parser import parse

import stewarxiv
from stewarxiv.evidence import gather_affiliation_evidence
from stewarxiv.names import approximate_name_lookup

log = logging.getLogger(__name__)

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
    if not stewarxiv.DEMO_MODE:
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

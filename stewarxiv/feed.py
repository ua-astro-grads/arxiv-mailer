"""Step 2: fetch the astro-ph RSS feed and keep postings by our people."""
import datetime
import logging

import feedparser
from bs4 import BeautifulSoup
from dateutil.parser import parse

from stewarxiv.evidence import gather_affiliation_evidence
from stewarxiv.names import Author, approximate_name_lookup

log = logging.getLogger(__name__)

def unpack_feed_entry(post, people, check_affiliation=True):
    """Turn one RSS feed entry into a post, if it's by our people.

    Splits the entry's comma-separated author list and matches each name with
    approximate_name_lookup; entries with no match are dropped. If
    check_affiliation is True, the LaTeX source is then checked with
    gather_affiliation_evidence, and the entry is dropped if the source has
    no UofA mention, or if it couldn't be read and the authors' match scores
    add up to less than 2. The abstract is the summary text after
    'Abstract: '.

    Args:
        post: A feedparser entry from the astro-ph RSS feed.
        people: Directory from build_directory.
        check_affiliation: Whether to download and check the LaTeX source
            (False in demo mode).

    Returns:
        dict | None: The post, with keys authors (list of Author), title,
        area, abstract, arxiv_id and html_arxiv_id; or None if dropped.
    """
    title = post.title
    arxiv_area = post.tags[0]['term']
    # New arXiv RSS feed has a comma-separated author list instead of the a tag
    author_names = [author.strip() for author in
        BeautifulSoup(post.author, features="lxml").text.split(',')]
    authors = [Author(name, *approximate_name_lookup(name, people)) for name in author_names]
    our_people_score = sum(item.score for item in authors)
    if our_people_score < 1:
        return
    else:
        log.info(f"Found {our_people_score=} from {authors=}")
    arxiv_id = post.link.rsplit('/', 1)[1]
    if check_affiliation:
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

def fetch_feed():
    """Download and parse the astro-ph RSS feed.

    Returns:
        feedparser.FeedParserDict: The feed. feed.entries are the postings;
        feed.feed holds its 'updated' and 'published' dates.
    """
    return feedparser.parse('https://rss.arxiv.org/rss/astro-ph')

def feed_is_fresh(feed):
    """Check that the feed is from today, so only new postings are sent.

    Converts the feed's 'updated' and 'published' dates to UTC and compares
    them with today's UTC date, logging a warning if either differs (e.g. on
    weekends, when arXiv doesn't announce new postings).

    Args:
        feed: The feed from fetch_feed.

    Returns:
        bool: True if both dates are today.
    """
    update_day = parse(feed.feed['updated']).astimezone(datetime.timezone.utc).date()
    pub_day = parse(feed.feed['published']).astimezone(datetime.timezone.utc).date()
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if (update_day - today).days != 0:
        log.warning(f"Mailer was invoked but feed was last updated on {update_day} UTC")
        return False
    if (pub_day - today).days != 0:
        log.warning(f"Mailer was invoked but content in feed was last " +
                    f"published on {pub_day} UTC")
        return False
    return True

def get_matching_posts(feed, people, check_affiliation=True):
    """Find the postings in the feed by our people.

    Runs unpack_feed_entry on every entry and keeps the ones it returns.
    Also collects the directory entry of every matched author, sorted by
    (last_name, first_names); someone on several posts appears once per
    post.

    Args:
        feed: The feed from fetch_feed.
        people: Directory from build_directory.
        check_affiliation: Passed to unpack_feed_entry (False in demo mode).

    Returns:
        tuple[list[dict], list[Person]]: (posts, all_authors).
    """
    posts = []
    all_authors = []
    for post in feed.entries:
        unpacked_post = unpack_feed_entry(post, people, check_affiliation)
        if unpacked_post:
            posts.append(unpacked_post)
            for author in unpacked_post['authors']:
                if author.key is not None:
                    key = author.key
                    all_authors.append((key, people[key]))
    # sorting by the key, so by last names
    all_authors.sort()
    all_authors = [x[1] for x in all_authors]

    return posts, all_authors

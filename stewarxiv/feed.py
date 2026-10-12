"""Step 2: fetch the astro-ph RSS feed and keep postings by our people."""
import datetime
import logging
import re
import unicodedata
import time

import feedparser
from bs4 import BeautifulSoup
from dateutil.parser import parse

from stewarxiv.evidence import AMBIGUOUS_RE, gather_affiliation_evidence
from stewarxiv.names import Author, approximate_name_lookup

log = logging.getLogger(__name__)

# LaTeX accent commands and the Unicode combining characters they add
LATEX_ACCENTS = {
    "'": '\u0301', '`': '\u0300', '^': '\u0302', '"': '\u0308', '~': '\u0303',
    '=': '\u0304', '.': '\u0307', 'u': '\u0306', 'v': '\u030c', 'H': '\u030b',
    'c': '\u0327', 'k': '\u0328', 'r': '\u030a', 'd': '\u0323', 'b': '\u0331',
}
# LaTeX commands for letters that aren't an accent on an ASCII letter
LATEX_LETTERS = {
    'ss': 'ß', 'aa': 'å', 'AA': 'Å', 'ae': 'æ', 'AE': 'Æ', 'oe': 'œ', 'OE': 'Œ',
    'i': 'ı', 'j': 'ȷ', 'o': 'ø', 'O': 'Ø', 'l': 'ł', 'L': 'Ł',
}
LATEX_LETTER_RE = re.compile(r'\\(ss|aa|AA|ae|AE|oe|OE|[ijoOlL])(?![a-zA-Z])\s*')
# symbol accents may be followed directly by the letter (\'a); letter accents
# need braces or a space (\v{s}, \v s) so \c is not read as part of \cdot
LATEX_ACCENT_RE = re.compile(
    r"""\\([\'`^"~=.]|[uvHckrdb](?=[\s{]))\s*(?:\{\s*(\w)\s*\}|(\w))""")

def latex_to_unicode(text):
    """Replace LaTeX accents and special letters with Unicode characters.

    arXiv author names are written in LaTeX, e.g. "Sebasti\\'an P\\'erez".
    Letter commands (\\o, \\ss, \\i, ...) are replaced first, then each accent
    command (\\'a, \\v{s}, \\c{C}, ...) becomes its letter plus a combining
    accent. A dotless i or j under an accent becomes a plain i or j, since
    \\'{\\i} means í. The result is NFC-normalized so 'a' plus a combining
    acute is the single character 'á', then any leftover grouping braces
    are removed. Other LaTeX, such as math, is left as it is.

    Args:
        text: Text containing LaTeX, e.g. "Sebasti\\'an P\\'erez".

    Returns:
        str: The text with Unicode letters, e.g. 'Sebastián Pérez'.
    """
    text = LATEX_LETTER_RE.sub(lambda m: LATEX_LETTERS[m[1]], text)

    def add_accent(match):
        accent, braced_letter, bare_letter = match.groups()
        letter = braced_letter or bare_letter
        letter = {'ı': 'i', 'ȷ': 'j'}.get(letter, letter)
        return letter + LATEX_ACCENTS[accent]

    text = LATEX_ACCENT_RE.sub(add_accent, text)
    text = unicodedata.normalize('NFC', text)
    return re.sub(r'(?<!\\)[{}]', '', text)

# seconds to wait before each LaTeX source download, to be polite to arXiv
DOWNLOAD_DELAY = 1

def unpack_feed_entry(post, people, check_affiliation=True):
    """Turn one RSS feed entry into a post, if it's by our people.

    Converts LaTeX accents in the author list to Unicode with
    latex_to_unicode, splits the comma-separated list, and matches each name
    with approximate_name_lookup. If check_affiliation is True, the LaTeX
    source is then checked with gather_affiliation_evidence.

    For entries with an author match, the entry is dropped if the source has
    no UofA mention, or if it couldn't be read and the authors' match scores
    add up to less than 2.

    Entries with no author match are dropped unless check_affiliation is True
    and the source was read and contains a department affiliation
    (AMBIGUOUS_RE, e.g. "Steward Observatory, University of Arizona"); those
    are returned with 'ambiguous' set to True. The abstract is the summary
    text after 'Abstract: '.

    Args:
        post: A feedparser entry from the astro-ph RSS feed.
        people: Directory from build_directory.
        check_affiliation: Whether to download and check the LaTeX source
            (False in demo mode).

    Returns:
        dict | None: The post, with keys authors (list of Author), title,
        area, abstract, arxiv_id, html_arxiv_id and ambiguous (True if
        there was no author match, only an affiliation match); or None if
        dropped.
    """
    title = post.title
    arxiv_area = post.tags[0]['term']
    # New arXiv RSS feed has a comma-separated author list instead of the a tag
    author_text = latex_to_unicode(BeautifulSoup(post.author, features="lxml").text)
    author_names = [author.strip() for author in author_text.split(',')]
    authors = [Author(name, *approximate_name_lookup(name, people)) for name in author_names]
    our_people_score = sum(item.score for item in authors)
    arxiv_id = post.link.rsplit('/', 1)[1]
    ambiguous = our_people_score < 1
    if ambiguous:
        if not check_affiliation:
            return
        # no author match: only keep it if the source names a UofA department
        time.sleep(DOWNLOAD_DELAY)
        evidence, gather_success = gather_affiliation_evidence(arxiv_id, AMBIGUOUS_RE)
        if not gather_success or evidence == 0:
            return
        log.info(f"Found ambiguous {arxiv_id=} with {evidence=}")
    else:
        log.info(f"Found {our_people_score=} from {authors=}")
    if check_affiliation and not ambiguous:
        time.sleep(DOWNLOAD_DELAY)
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
        'ambiguous': ambiguous,
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

    Runs unpack_feed_entry on every entry and keeps the ones it returns,
    split into posts with an author match and ambiguous posts (affiliation
    match only). Also collects the directory entry of every matched author,
    sorted by (last_name, first_names); someone on several posts appears once
    per post.

    Args:
        feed: The feed from fetch_feed.
        people: Directory from build_directory.
        check_affiliation: Passed to unpack_feed_entry (False in demo mode).

    Returns:
        tuple[list[dict], list[Person], list[dict]]: (posts, all_authors,
        ambiguous_posts).
    """
    posts = []
    ambiguous_posts = []
    all_authors = []
    for post in feed.entries:
        unpacked_post = unpack_feed_entry(post, people, check_affiliation)
        if unpacked_post and unpacked_post['ambiguous']:
            ambiguous_posts.append(unpacked_post)
        elif unpacked_post:
            posts.append(unpacked_post)
            for author in unpacked_post['authors']:
                if author.key is not None:
                    key = author.key
                    all_authors.append((key, people[key]))
    # sorting by the key, so by last names
    all_authors.sort()
    all_authors = [x[1] for x in all_authors]

    return posts, all_authors, ambiguous_posts

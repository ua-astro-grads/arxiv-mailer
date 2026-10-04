"""Step 1: build the personnel directory by scraping astro.arizona.edu."""
import logging
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

from stewarxiv.names import normalize_caseless

log = logging.getLogger(__name__)

def soupify(url):
    """Fetch a web page and parse it into a BeautifulSoup tree.

    Requests the page with SSL certificate verification turned off (and the
    resulting warnings silenced), then parses the HTML with lxml.

    Args:
        url: Full URL of the page.

    Returns:
        BeautifulSoup: The parsed page.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        req = requests.get(url, verify=False)
    return BeautifulSoup(req.text, features="lxml")

FACULTY = 1
POSTDOC = 2
STAFF = 2
STUDENT = 3

# A directory entry: what build_directory stores for each person, keyed by
# their normalized (last_name, first_names). It's a plain dict at runtime;
# the types just document the keys.
class _PersonFields(TypedDict):
    role: int               # FACULTY, POSTDOC, STUDENT or STAFF
    position: str           # job title, e.g. 'Graduate Student'; '' if the profile has none
    image: str | None       # headshot URL, or None if the profile has none
    page: str               # profile page URL

class Person(_PersonFields, total=False):
    thumb_cid: str          # added by thumbnails.build_thumbnails when the headshot is embedded

# Each listing page shows names differently on its .card-body cards
def name_from_fields(card):
    """Read a name from a listing card with separate first/last name fields.

    Looks inside the card's <h1> for the first-name and last-name elements
    (classes field--name-field-az-fname and -lname) and strips whitespace.
    Used for the faculty, graduate student and staff pages.

    Args:
        card: A .card-body element from a listing page.

    Returns:
        tuple[str, str]: (first_name, last_name) as shown on the page.

    Raises:
        AttributeError: If the card has no <h1> or name fields.
    """
    h1 = card.select_one('h1')
    firstname = h1.select_one('.field--name-field-az-fname').text.strip()
    lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
    return (firstname, lastname)

def name_from_h3(card):
    """Read a name from a listing card that shows it as one string.

    Takes the text of the card's first <h3>, removes newlines, and splits it
    at the first space, so 'Mary Ann Evans' becomes ('Mary', 'Ann Evans').
    Used for the postdoc page.

    Args:
        card: A .card-body element from a listing page.

    Returns:
        tuple[str, ...]: (first_name, rest_of_name), or a 1-tuple if the
        name has no space.

    Raises:
        IndexError: If the card has no <h3>.
    """
    return tuple(card.select('h3')[0].text.replace('\n', '').split(' ', 1))

# The listing pages to scrape, in order (a later page overwrites an earlier
# one for the same name): (path, role, how to read names, position).
# A position of None means read it from each person's profile page (blank
# if the profile doesn't list one).
DIRECTORY_PAGES = [
    ('/people/all-faculty', FACULTY, name_from_fields, None),
    ('/people/postdocs', POSTDOC, name_from_h3, None),
    ('/people/graduate-students', STUDENT, name_from_fields, 'Graduate Student'),
    ('/people/staff', STAFF, name_from_fields, 'Staff'),
]

def build_directory() -> dict[tuple[str, ...], Person]:
    """Scrape the department website into a directory of people.

    For each listing page in DIRECTORY_PAGES, reads every .card-body card:
    gets the name with that page's name reader, normalizes it into a
    lowercase (last_name, first_names) key, then opens the person's profile
    page for their position (or uses the page's fixed position) and headshot
    URL. A missing position is logged and stored as '' (the person is still
    included, so their papers are matched); a missing headshot is logged and
    stored as None. If a name appears on several pages, the later page's
    entry wins.

    Returns:
        dict[tuple[str, ...], Person]: Directory entries keyed by
        (last_name, first_names).
    """
    people = {}
    base_link = 'https://astro.arizona.edu'

    for path, role, read_name, fixed_position in DIRECTORY_PAGES:
        listing_page = soupify(base_link + path)
        for wrap in listing_page.select('.card-body'):
            name = read_name(wrap)
            name = tuple(normalize_caseless(part.strip()) for part in name)[::-1] # lower case and reverse order

            # retrieve link to individual page
            ind_page_link = wrap.find_all('a', href=True)[0]['href']
            ind_page = soupify(base_link + ind_page_link)

            # get position
            if fixed_position is None:
                try:
                    position = ind_page.find_all("div", class_="field--name-field-az-titles")[0].text.replace('\n', '')
                except Exception:
                    # keep them anyway: skipping meant their papers were
                    # never matched (issue #17)
                    log.warning(f"Failed to get position for {name}; keeping them with a blank position")
                    position = ''
            else:
                position = fixed_position

            # get image
            try:
                image = base_link + ind_page.select('article')[0].select_one('img')['src']
            except Exception:
                log.warning(f"Unable to find image for {name}")
                image = None

            people[name] = {
                'role': role,
                'position': position,
                'image': image,
                'page': base_link + ind_page_link,
            }

    print("finished building directory")

    return people

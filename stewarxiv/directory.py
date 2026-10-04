"""Step 1: build the personnel directory by scraping astro.arizona.edu."""
import logging
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

from stewarxiv.names import normalize_caseless

log = logging.getLogger(__name__)

def soupify(url):
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
    position: str           # job title, e.g. 'Graduate Student'
    image: str | None       # headshot URL, or None if the profile has none
    page: str               # profile page URL

class Person(_PersonFields, total=False):
    thumb_cid: str          # added by thumbnails.build_thumbnails when the headshot is embedded

# Each listing page shows names differently on its .card-body cards
def name_from_fields(card):
    # separate first and last name fields inside the card's <h1>
    h1 = card.select_one('h1')
    firstname = h1.select_one('.field--name-field-az-fname').text.strip()
    lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
    return (firstname, lastname)

def name_from_h3(card):
    # "First Last" as one string in the card's <h3>
    return tuple(card.select('h3')[0].text.replace('\n', '').split(' ', 1))

# The listing pages to scrape, in order (a later page overwrites an earlier
# one for the same name): (path, role, how to read names, position).
# A position of None means read it from each person's profile page, and
# skip the person if it's missing.
DIRECTORY_PAGES = [
    ('/people/all-faculty', FACULTY, name_from_fields, None),
    ('/people/postdocs', POSTDOC, name_from_h3, None),
    ('/people/graduate-students', STUDENT, name_from_fields, 'Graduate Student'),
    ('/people/staff', STAFF, name_from_fields, 'Staff'),
]

def build_directory() -> dict[tuple[str, ...], Person]:
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
                    log.warning(f"Failed to get position for {name}")
                    continue
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

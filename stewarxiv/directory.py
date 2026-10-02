"""Step 1: build the personnel directory by scraping astro.arizona.edu."""
import logging

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

def build_directory():
    people = {}
    base_link = 'https://astro.arizona.edu'

    faculty_page = soupify('https://astro.arizona.edu/people/all-faculty')
    for facwrap in faculty_page.select('.card-body'):

        h1 = facwrap.select_one('h1')
        firstname = h1.select_one('.field--name-field-az-fname').text.strip()
        lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
        name = (firstname, lastname)
        name = tuple(normalize_caseless(part.strip()) for part in name)[::-1]

        # retrieve link to individual page
        ind_page_link = facwrap.find_all('a', href=True)[0]['href']
        ind_page = soupify(base_link + ind_page_link)

        # get position
        try:
            position = ind_page.find_all("div", class_="field--name-field-az-titles")[0].text.replace('\n', '')
        except Exception as e:
            log.warning(f"Failed to get position for {name}")
            continue
        # get image
        try:
            image = base_link + ind_page.select('article')[0].select_one('img')['src']
        except Exception as e:
            log.warning(f"Unable to find image for {name}")
            image = None

        people[name]= {
            'role': FACULTY,
            'position': position,
            'image': image, 
            'page': base_link + ind_page_link,
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
        except Exception as e:
            log.warning(f"Failed to get position for {name}")
            continue
        
        # get image
        try:
            image = base_link + ind_page.select('article')[0].select_one('img')['src']
        except Exception as e:
            log.warning(f"Unable to find image for {name}")
            image = None

        people[name]= {
            'role': POSTDOC,
            'position': position,
            'image': image,
            'page': base_link + ind_page_link,
        }

    student_page = soupify('https://astro.arizona.edu/people/graduate-students')
    for wrap in student_page.select('.card-body'):

        h1 = wrap.select_one('h1')
        firstname = h1.select_one('.field--name-field-az-fname').text.strip()
        lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
        name = (firstname, lastname)
        name = tuple(normalize_caseless(part.strip()) for part in name)[::-1]

        # retrieve link to individual page
        ind_page_link = wrap.find_all('a', href=True)[0]['href']
        ind_page = soupify(base_link + ind_page_link)

        # get image
        try:
            image = base_link + ind_page.select('article')[0].select_one('img')['src']
        except Exception as e:
            log.warning(f"Unable to find image for {name}")
            image = None

        people[name]= {
            'role': STUDENT,
            'position': 'Graduate Student',
            'image': image,
            'page': base_link + ind_page_link,
        }

    staff_page = soupify('https://astro.arizona.edu/people/staff')
    for wrap in staff_page.select('.card-body'):

        h1 = wrap.select_one('h1')
        firstname = h1.select_one('.field--name-field-az-fname').text.strip()
        lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
        name = (firstname, lastname)
        name = tuple(normalize_caseless(part.strip()) for part in name)[::-1]

        # retrieve link to individual page
        ind_page_link = wrap.find_all('a', href=True)[0]['href']
        ind_page = soupify(base_link + ind_page_link)

        # get image
        try:
            image = base_link + ind_page.select('article')[0].select_one('img')['src']
        except Exception as e:
            log.warning(f"Unable to find image for {name}")
            image = None

        people[name]= {
            'role': STAFF,
            'position': 'Staff',
            'image': image,
            'page': base_link + ind_page_link,
        }

    print("finished building directory")

    return people

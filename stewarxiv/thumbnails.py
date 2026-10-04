"""Crop matched authors' headshots into small round PNGs to embed in the email."""
import io
import logging
from email.utils import make_msgid

import requests
from PIL import Image, ImageDraw, ImageOps

log = logging.getLogger(__name__)

# headshots are shown at 40x40, so render at 2x for high-DPI screens
THUMB_SIZE = 80

def make_thumbnail(url):
    """Download a headshot and turn it into a small round PNG.

    Crops the image to a square, centered horizontally and shifted toward
    the top where the face usually is (ImageOps.fit), instead of letting the
    email client stretch it. Then makes the corners transparent with a
    circular mask, drawn at 4x size and scaled down for smooth edges, so it
    is round even in clients that ignore border-radius (Outlook). Saves it as
    a 256-color PNG, which keeps the transparency at about a third of the
    file size.

    Args:
        url: URL of the headshot image.

    Returns:
        bytes: PNG data, THUMB_SIZE x THUMB_SIZE pixels.

    Raises:
        requests.HTTPError: If the download fails.
        PIL.UnidentifiedImageError: If the file isn't an image.
    """
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = requests.get(url, verify=False, timeout=30)
    res.raise_for_status()
    img = Image.open(io.BytesIO(res.content)).convert('RGBA')
    thumb = ImageOps.fit(img, (THUMB_SIZE, THUMB_SIZE), centering=(0.5, 0.3))
    # draw the mask at 4x and downsample for anti-aliased edges
    mask = Image.new('L', (4 * THUMB_SIZE, 4 * THUMB_SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 4 * THUMB_SIZE - 1, 4 * THUMB_SIZE - 1), fill=255)
    thumb.putalpha(mask.resize((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS))
    # 256-color palette PNG keeps transparency at ~1/3 the size of full color
    buff = io.BytesIO()
    thumb.quantize(256).save(buff, 'PNG', optimize=True)
    return buff.getvalue()

def build_thumbnails(all_authors):
    """Make an embeddable thumbnail of each author's headshot.

    Skips people with no headshot and people already done (someone on
    several posts is in the list more than once). For each thumbnail it
    generates a unique content ID and stores it on the person as
    'thumb_cid', which the template uses as the image source (cid:...). If a
    headshot can't be downloaded or read, a warning is logged and that
    person gets no thumbnail.

    Args:
        all_authors: Person entries from get_matching_posts; modified in
            place.

    Returns:
        dict[str, bytes]: PNG data keyed by content ID, for compose_email.
    """
    thumbnails = {}
    for person in all_authors:
        if 'thumb_cid' in person or not person['image']:
            continue
        try:
            png = make_thumbnail(person['image'])
        except Exception as e:
            log.warning(f"Unable to make thumbnail from {person['image']}: {e}")
            continue
        cid = make_msgid(domain='stewarxiv')[1:-1]  # strip the <>
        person['thumb_cid'] = cid
        thumbnails[cid] = png
    return thumbnails

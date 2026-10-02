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
    # crop to a centered square (biased up toward the face) instead of
    # letting the email client stretch it, then bake in a circular mask so
    # it's round even in clients that ignore border-radius (Outlook)
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
    # returns {cid: png bytes} and sets 'thumb_cid' on each author with a
    # thumbnail, which the template uses to reference the inline image
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

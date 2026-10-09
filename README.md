# StewarXiv arXiv mailer

Emails a daily digest of new astro-ph postings by University of Arizona astronomy people (faculty, postdocs, grad students and staff) to the astro-stewarxiv mailing list.

## Quick start
```
python3 -m venv mailer_env
source mailer_env/bin/activate
python3 -m pip install -r requirements.txt
cp config.py.template config.py
mkdir logs
python mailer.py -d        # demo run, see "Demo mode" below
```

## Configuration
`config.py` (gitignored, copied from `config.py.template`) sets the SMTP server (`smtp.gmail.com:465`) and reads these environment variables:

| Variable | Meaning |
|---|---|
| `MAIL_USERNAME` | account the mail is sent from; also the admin address |
| `MAIL_PASSWORD` | its password; for CatMail, use the secondary password ([SMTP settings](https://uarizona.service-now.com/sp?id=kb_article_view&sysparm_article=KB0010181)) |
| `MAIL_SENDTO` | the list address (default `astro-stewarxiv@list.arizona.edu`) |

## How it works
`mailer.py` runs these steps in order. The code for each lives in `stewarxiv/`:

| Step | Module | What it does |
|---|---|---|
| 1. Directory | `directory.py` | Scrapes the astro.arizona.edu people pages into `Person` entries keyed by `(last_name, first_names)`. The pages and how each shows names are in the `DIRECTORY_PAGES` table: start there if the website layout changes. People whose profile lists no job title are kept with a blank position. Nicknames in parentheses or quotes ("Robert S. (Bob)") are dropped, since they're unlikely to be the publishing name. |
| 2. Feed | `feed.py` | Fetches the astro-ph RSS feed, stops if it wasn't updated today, converts LaTeX accents in author names to Unicode (`Sebasti\'an` → `Sebastián`), and keeps postings with an author match. |
| 2a. Names | `names.py` | `approximate_name_lookup` scores each arXiv author 0 (no match), 1 (first initial + last name) or 2 (full name; a middle initial on only one side is ignored), giving an `Author(name, key, score)`. Accents are ignored (Dániel matches Daniel). Multi-word and hyphenated surnames match; if the directory has only the first part of the surname (Faramaz for Faramaz-Gorka) the score is at most 1. |
| 2b. Evidence | `evidence.py` | For matched postings, downloads the LaTeX source and counts UofA affiliation strings (`UOFA_RE`). Postings with none are dropped. If the source can't be downloaded, a posting is kept only if its authors' scores add up to 2 or more. |
| 3. Thumbnails | `thumbnails.py` | Crops the matched authors' headshots into small round images embedded in the email. |
| 4. Email | `mailing.py` | Renders the Jinja2 templates in `templates/` (`mailing.jinja2.html`, `mailing.jinja2.txt`, `author.jinja2.html`), builds the message and sends it. |

If there are matching postings the email goes to the list; otherwise only to the admin address. Each run logs to `logs/<date>.log`.

## Demo mode
`python mailer.py -d` (or `--demo`) is the way to try changes:

- skips the affiliation check (step 2b)
- writes `mailing.html` (open in a browser), `mailing.txt` and `mailing.eml` (open in a mail client)
- sends only to the admin address, never the list
- saves the day's data to `demo.pickle` and reuses it on later runs, skipping the scraping and the feed. Keep a pickle from a day with UofA papers to work on weekends or quiet days; delete it to refresh.

`python mailer.py --help` lists the options.

## Tests
```
python -m pip install pytest
python -m pytest
```
Run from the repo root with `python -m pytest` (not plain `pytest`) so the tests can import `stewarxiv`.

## Deployment
Run it on an always-on machine on weekdays at 11:00 UTC (cron or a systemd timer), either directly or with Docker:
```
mkdir logs
docker run \
	-e MAIL_USERNAME=<username> \
	-e MAIL_PASSWORD=<password> \
	-v logs:/arxiv-mailer/logs \
	noahfranz13/stewarxiv:v0.1
```
The Dockerfile clones the repo's default branch (`main`), so merge changes there first, then rebuild with `docker build -t stewarxiv:<version> .`

When testing a new setup, have the list owner hold messages for moderation at [list.arizona.edu](https://list.arizona.edu/sympa/info/astro-stewarxiv) so test emails don't reach subscribers.

## Development workflow (Vikram)
1. Load the mailer environment
2. In a terminal: `python mailer.py` (add `-d` for demo mode)
3. In the VS Code debugger: run from the debug panel so it uses the correct environment

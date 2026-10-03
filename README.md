# Run through docker
```
mkdir logs
docker run \
	-e MAIL_USERNAME=<username> \
	-e MAIL_PASSWORD=<password> \
	-v logs:/arxiv-mailer/logs \
	noahfranz13/stewarxiv:v0.1
```

# Development: Building the docker container
After making changes run
```
docker build -t stewarxiv:v....
```

# Install requirements in a python venv
```
python3 -m venv mailer_env
source mailer_env/bin/activate
python3 -m pip install -r requirements.txt
```

Use your favorite tool to schedule it to run, on a computer that stays on/online (maybe CSG has a server you can borrow?) I had the timer set to run Mon,Tue,Wed,Thu,Fri \*-\*-\* 11:00:00 UTC. You will need to set a few environment variables (described below, Step 4).

Here's what the script does. `mailer.py` runs these steps in order; the code for each step lives in the `stewarxiv/` package:

1. Build the personnel directory from the department website. If you've ever done web scraping before, it is straightforward code, but (as long as it's working) not important exactly how it accomplishes that. It grabs names (used as a dict key in the form (last_name, first_names)), headshot ('image'), and role (fac, postdoc, student). Code: `stewarxiv/directory.py`

2. Fetch the arxiv RSS feed (fetch_feed), stop if it wasn't updated today (feed_is_fresh), and filter it (get_matching_posts), all in `stewarxiv/feed.py`. The maybe confusingly named "unpack_feed_entry" returns None when there is not enough evidence that this is UofA people.

        2.a. This is where it gets a little hairy: approximate_name_lookup (`stewarxiv/names.py`) gives a score of 0, 1, or 2 based on the criteria commented there.
        2.b. If a score of 1 or greater is found, it goes to inspect the evidence.

                gather_affiliation_evidence (`stewarxiv/evidence.py`) retrieves the LaTeX source of the arxiv posting (no idea what happens for postings without it, hopefully nobody's posting word docs on astro-ph). It does a case-insensitive search through the whole text for some institution names and domains (see UOFA_RE) and counts the matches as an evidence score. This can push a first initial last name match over the threshold for inclusion, or skip a posting if none of those strings appear anywhere in the tex source (you'd expect at least 'university of arizona' to appear somewhere!)

3. Generate the email:

        3.a. build_thumbnails (`stewarxiv/thumbnails.py`) downloads the matched authors' headshots and crops them into small round images, which are embedded in the email

        3.b. The render_mailing function (`stewarxiv/email.py`) takes a "context" dictionary, and uses Jinja2 (a text templating language) to generate the mailing from snippets of text or HTML in the .jinja2.html files

        3.c. The compose_email function (`stewarxiv/email.py`) attaches the addresses, HTML and text versions of the email, and the subject line to an EmailMessage object the Python stdlib mail support knows how to send

4. Send the email (send_email in `stewarxiv/email.py`): The script reads environment variables $MAIL_SERVER $MAIL_PORT $MAIL_USERNAME and $MAIL_PASSWORD (so you don't have to have those in the script itself). You have to use the CatMail secondary password and SMTP settings from here https://uarizona.service-now.com/sp?id=kb_article_view&sysparm_article=KB0010181

Running `python mailer.py -d` (or `--demo`) turns on demo mode, which skips the affiliation check, sends only to the admin address instead of the list, and writes the mailing to "mailing.html", "mailing.txt" and "mailing.eml". Since emails are plain text, the .eml file will just open in your mail client, and is a good way to preview what your changes look like. Run `python mailer.py --help` to see the options.

The demo mode also pickles some data structures, which can be useful if you want to speed up your own iteration time working on a bug fix. This also persists the given day's matching posts, which means you can keep a pickle from a day with UofA papers and work on the script on a day without them, iirc. Should be basically transparent, and you can always remove demo.pickle if you change the data structure or need to refresh it for any reason.

Anyway, I would suggest:

1. Get the code and install the dependencies
2. Use the '-d' command line arg to run in demo mode to check the feed-parsing and email-generating, but not the email-sending
3. Get the credentials set up for outgoing mail
4. We can change the list config here so that outbound email gets stopped at the list during testing.
5. Test your config to make sure messages get to the list
6. Set up scheduled task on your desktop or a Steward server (with crontab or SystemD timers as you prefer)
7. We change the list config back so your messages go straight through without going to a queue
8. I disable my instance of the arxiv-mailer
9. Go to sleep and hope for the best the next day!


## Running tests
The tests live in `tests/`. Run them from the repo root with
```
python -m pytest
```
(use `python -m pytest` rather than plain `pytest` so the tests can import the `stewarxiv` package). Install pytest into your environment first if needed (`python -m pip install pytest`).

Known failure: `test_approximate_name_lookup` currently fails on the `'bob dave'` case (it's not matched to `('dave', 'a. bob c.')`).

## Development Workflow (Vikram)

1. Load mailer environment
2. If running the file in terminal: python mailer.py
3. If running the file in the debugger, open the debug panel on the left of vscode and then run from there to ensure you are running in the correct environment.

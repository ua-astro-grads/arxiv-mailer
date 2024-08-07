There's a handful of dependencies, and I don't have a requirements file or anything, but:

        pip install BeautifulSoup4 requests jinja2 feedparser

should cover it. You probably have all of them already, except perhaps feedparser.

Use your favorite tool to schedule it to run, on a computer that stays on/online (maybe CSG has a server you can borrow?) I had the timer set to run Mon,Tue,Wed,Thu,Fri \*-\*-\* 11:00:00 UTC. You will need to set a few environment variables (described below, Step 4).

Here's what the script does:

1. Build the personnel directory from the department website. If you've ever done web scraping before, it is straightforward code, but (as long as it's working) not important exactly how it accomplishes that. It grabs names (used as a dict key in the form (last_name, first_names)), headshot ('image'), and role (fac, postdoc, student)

2. Fetch the arxiv RSS feed and filter it (get_matching_posts). The maybe confusingly named "unpack_feed_entry" returns None when there is not enough evidence that this is UofA people.

        2.a. This is where it gets a little hairy: approximate_name_lookup gives a score of 0, 1, or 2 based on the criteria commented there.
        2.b. If a score of 1 or greater is found, it goes to inspect the evidence.

                gather_affiliation_evidence retrieves the LaTeX source of the arxiv posting (no idea what happens for postings without it, hopefully nobody's posting word docs on astro-ph). It does a case-insensitive search through the whole text for some institution names and domains (see UOFA_RE) and counts the matches as an evidence score. This can push a first initial last name match over the threshold for inclusion, or skip a posting if none of those strings appear anywhere in the tex source (you'd expect at least 'university of arizona' to appear somewhere!)

3. Generate the email:

        3.b. The render_mailing function takes a "context" dictionary, and uses Jinja2 (a text templating language) to generate the mailing from snippets of text or HTML in the .jinja2.html files

        3.c. The compose_email function attaches the addresses, HTML and text versions of the email, and the subject line to an EmailMessage object the Python stdlib mail support knows how to send

4. Send the email: The script reads environment variables $MAIL_SERVER $MAIL_PORT $MAIL_USERNAME and $MAIL_PASSWORD (so you don't have to have those in the script itself). You have to use the CatMail secondary password and SMTP settings from here https://uarizona.service-now.com/sp?id=kb_article_view&sysparm_article=KB0010181

There's a big global `DEMO_MODE` at the top that switches off the actual mailing and switches on writing a ".eml" file. Since emails are plain text, this will just open in your mail client, and is a good way to preview what your changes look like.

The demo mode also pickles some data structures, which can be useful if you want to speed up your own iteration time working on a bug fix. This also persists the given day's matching posts, which means you can keep a pickle from a day with UofA papers and work on the script on a day without them, iirc. Should be basically transparent, and you can always remove demo.pickle if you change the data structure or need to refresh it for any reason.

Anyway, I would suggest:

1. Get the code and install the dependencies
2. Either edit the global or use the '-d' command line arg to run in DEMO_MODE to check the feed-parsing and email-generating, but not the email-sending
3. Get the credentials set up for outgoing mail
4. We can change the list config here so that outbound email gets stopped at the list during testing.
5. Test your config to make sure messages get to the list
6. Set up scheduled task on your desktop or a Steward server (with crontab or SystemD timers as you prefer)
7. We change the list config back so your messages go straight through without going to a queue
8. I disable my instance of the arxiv-mailer
9. Go to sleep and hope for the best the next day!

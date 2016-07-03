from collections import namedtuple
from pprint import pprint
import re
import random
import time

from concurrent import futures

from google.appengine.api import urlfetch, memcache
from google.appengine.ext import deferred, ndb

class JobModel(ndb.Model):
    root = ndb.StringProperty(required=True)
    type = ndb.StringProperty(required=True, choices=('BFS', 'DFS'))
    depth = ndb.IntegerProperty(required=True)

class JobResultsModel(ndb.Model):
    results = ndb.PickleProperty(repeated=True)

class PageNode:
    """This class represents a page 'node' in the tree graph.
    id is the assigned ID number
    url is the page url
    favicon, if present, is the url to the site's favicon
    parent is the ID of the parent node. None denotes a root node

    jsonify() - returns a JSON-able representation of the node"""
    id_counter = 0
    def __init__(self, id, url, favicon=None, parent=None):
        self.id = id
        self.url = url
        self.favicon = favicon
        self.parent = parent

    def jsonify(self):
        return self.__dict__

class TerminationSentinal:
    pass

link_regex = re.compile(r'''<a [^>]*href=['"]?(?P<link>(https?://)?([a-z0-9\-]+\.){1,2}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]''', re.I)
"""
Explanation of regex:
<a [^>]*href=['"]?(?P<link>(https?://)?([a-z0-9\-]+\.){1,2}[a-z0-9]+(?<!\.html)((\?|/)[^'" ]*)?)['" ]

Start with an anchor '<a ', followed by a any number of other characters except the closing >
until 'href=' is encountered

Match either ' or " or no quotes
Name the resulting link (the group in the outer most paranthesis) 'link' for easy identification later

Links can start with http:// or https://, but don't have to (match 0 or 1 times)
Links must have a group of alphanumberic + '-' characters, followed by a '.'. Links must have EITHER 1 or 2 of these

EX: github.com has 1 set of characters followed by a period, www.google.com has two

Following the last period, links must have another set of alphanumeric + '-' characters

(?<!\.html) lets us look at the last 5 characters. If they are .html, this must be a local link in teh form
somepage.html, in which case we do not want this link, so do not match

Links can end there, but don't have to. ((\?|/)[^'" ]*)? gets further links (optional)

(\?|/) first matches either ? (for query strings) or / (for routes)
[^'" ]* than matches any number of characters of any kind until it reaches a quote or space. The final ? means this
entire part is optional

The final ['" ] matches the closing quote or space.
"""

# regex to match just the host (including leading http...)
host_regex = re.compile(r'''https?://([a-z0-9\-]+\.){1,2}[a-z0-9]+''')

def to_utf8(str_or_unicode):
    return unicode(str_or_unicode, 'utf-8', errors='replace')

def get_host(url):
    """Extracts and returns just the service + host from url"""
    return host_regex.match(url).group()

def extract_links(page):
    return [match.group('link') for match in link_regex.finditer(page)]

def get_page(url, id, end_phrase=None, parent=None):
    """Retrieves the page pointed to by URL, extracts the links, and returns a tuple of a PageNode of this page,
    and a list of all the extracted links"""

    try:
        res = urlfetch.fetch(url)
    except:
        return None, None, None

    if res.status_code != 200:
        return None, None, None

    page = to_utf8(res.content)

    # discard links to the same host
    host = get_host(url)
    links = [link for link in extract_links(page) if not link.startswith(host)]

    pprint("Links contained in {}: ".format(url))
    pprint(links)

    if end_phrase and page.find(end_phrase) != -1:
        print "End phrase find!"
        phrase_found = True
    else:
        phrase_found = False

    return (PageNode(id, url, parent=parent, favicon=get_favicon(url)), links, phrase_found)

def get_favicon(url):
    """Attempts to get the site's favicon. If successful, returns the URL. On failure, returns None"""
    # use a regex to get the host
    match = host_regex.match(url)

    favicon_url = get_host(url) + '/favicon.ico'

    if urlfetch.fetch(favicon_url).status_code == 200:
        return favicon_url
    else:
        return None

def start_crawler(url, search_type, max_depth=3, end_phrase=None):
    """Starts a crawler job. On success, returns a 2-tuple of the root node and the job ID
    On failure, returns None"""

    #Ensure that our link starts with http
    if not url.startswith('http'):
        url = 'http://' + url

    # First get the root page. This validates that the URL is valid, so we can start and return something useful
    root, links, _ = get_page(url, 0)

    if search_type == 'DFS':
        crawler = depth_first_crawl
    else:
        crawler = bredth_first_crawl

    job = JobModel(root=url, type=search_type, depth=max_depth)
    job.put()

    job_id = job.key.id()

    deferred.defer(run_crawler, job_id, crawler, links, max_depth, end_phrase)

    return root, job_id

def run_crawler(job_id, crawler, links, max_depth, end_phrase):
    """Executes the specified crawl, saving results to the memcache for retrieval by the front-facing components"""

    output_buffer = []
    cache = memcache.Client()
    job_key = JobModel.get_by_id(job_id).key

    timer_start = time.time()

    for node in crawler(links, max_depth, end_phrase):
        output_buffer.append(node)

        if time.time() - timer_start >= 2:
            # write a new result as a child of the JobModel
            JobResultsModel(results=list(output_buffer), parent=job_key).put()
            output_buffer = []
            timer_start = time.time()

    # we're done with the crawl. Append the termination sentinal to the results before pushing the last batch
    output_buffer.append(TerminationSentinal())
    JobResultsModel(results=list(output_buffer), parent=job_key).put()

def depth_first_crawl(starting_links, max_depth, end_phrase=None, parent_id=0):
    """Generator function which yields successive nodes in a depth first style
    Begins with a randomly selected link from links"""
    links = list(starting_links)
    cur_id = parent_id + 1
    cur_parent = parent_id

    for i in range(max_depth):
        # if there are no links here, return
        if len(links) == 0:
            return

        # get a random link to follow
        link = random.choice(links)
        node, links, phrase_found = get_page(link, cur_id, end_phrase, cur_parent)

        # if this page was unaccessible, continue to the next loop. Continue before incrementing cur_id or yielding
        if not node:
            continue

        yield node

        if phrase_found:
            return

        cur_parent = cur_id
        cur_id += 1

def bredth_first_crawl(starting_links, max_depth, end_phrase=None, parent_id=0):
    """Generator function which yields successive nodes in a bredth first style"""
    cur_id = parent_id + 1

    # simple tuple to associate parent IDs to the list of links
    PageLinks = namedtuple('PageLinks', 'parent links')

    current_links = [PageLinks(parent_id, list(starting_links))]

    for i in range(max_depth):
        next_level_links = []

        for parent, links in current_links:
            #getting a bunch of pages at once is what ThreadPool was born for!
            with futures.ThreadPoolExecutor(max_workers=5) as executor:
                results = []

                # load up the workers with all our pages to retrieve and parse
                for link in links:
                    results.append(executor.submit(get_page, link, cur_id, end_phrase, parent))
                    cur_id += 1

                # process and yield the pages as completed
                for res in futures.as_completed(results):
                    new_node, new_links, phrase_found = res.result()

                    if not new_node:
                        #just like DFS, if the page is unaccessible, then skip it
                        continue

                    yield new_node

                    if phrase_found:
                        return

                    # append the list of links with the parent to the next level links, increment the cur_id
                    next_level_links.append(PageLinks(new_node.id, new_links))



        current_links = list(next_level_links)


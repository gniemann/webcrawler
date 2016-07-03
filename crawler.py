from collections import namedtuple
from pprint import pprint
import re
import random
import time

from concurrent import futures

from google.appengine.api import urlfetch, memcache
from google.appengine.ext import deferred, ndb

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

def retrieve_url(url):
    """Attempts to GET the url. If unsuccessful, returns None and lets the caller deal with it
    This function is designed to abstract away GAE specific code"""
    try:
        return urlfetch.fetch(url)
    except:
        return None

def to_utf8(str_or_unicode):
    return unicode(str_or_unicode, 'utf-8', errors='replace')

def get_host(url):
    """Extracts and returns just the service + host from url"""
    return host_regex.match(url).group()


def extract_links(page):
    page = to_utf8(page)
    return [match.group('link') for match in link_regex.finditer(page)]

def get_favicon(url):
    """Attempts to get the site's favicon. If successful, returns the URL. On failure, returns None"""
    # use a regex to get the host
    match = host_regex.match(url)

    favicon_url = get_host(url) + '/favicon.ico'

    if urlfetch.fetch(favicon_url).status_code == 200:
        return favicon_url
    else:
        return None

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

    on creation, loads the page and parses links

    jsonify() - returns a JSON-able representation of the node"""
    def __init__(self, id, url, parent=None, depth=0, end_phrase=None):
        self.id = id
        self.depth = depth
        self.parent = parent

        # Ensure that our link starts with http
        if not url.startswith('http'):
            url = 'http://' + url

        self.url = url

        res = retrieve_url(url)

        # if we could not retrieve a page, raise an exception to ensure that this page is not created
        if res is None or res.status_code != 200:
            raise TypeError("Page is not retrievable")

        host = get_host(url)
        self.links = [link for link in extract_links(res.content) if not link.startswith(host)]

        if end_phrase and to_utf8(res.content).find(end_phrase) != -1:
            self.phrase_found = True
        else:
            self.phrase_found = False

        self.favicon = get_favicon(url)

    def jsonify(self):
        return dict({'id': self.id,
                     'parent': self.parent,
                     'url': self.url,
                     'favicon': self.favicon,
                     'depth': self.depth})

class TerminationSentinal:
    """Signals the end of the search"""
    pass

def crawler_output_to_datastore(job_key, output_list):
    JobResultsModel(results=list(output_list), parent=job_key).put()

class Crawler:
    """Base class for crawlers.
    Derived classes must overide the crawl method to implement desired behavior"""
    def __init__(self, job_key, output_func, max_depth=1, end_phrase=None):
        self.job_key = job_key
        self.max_depth = max_depth
        self.end_phrase = end_phrase
        self.output_func = output_func

    def __call__(self, links):
        output_buffer = []

        timer_start = time.time()

        for node in self.crawl(links):
            output_buffer.append(node)

            # write every 2 seconds
            if time.time() - timer_start >= 2:
                self.output_func(self.job_key, output_buffer)
                output_buffer = []
                timer_start = time.time()

        # we're done with the crawl. Append the termination sentinal to the results before pushing the last batch
        output_buffer.append(TerminationSentinal())
        self.output_func(self.job_key, output_buffer)

    def crawl(self, starting_links):
        raise NotImplemented

class DepthFirstCrawler(Crawler):
    def crawl(self, starting_links):
        links = list(starting_links)
        cur_parent = 0
        cur_id = cur_parent + 1

        for i in range(1, self.max_depth + 1):
            # if there are no links here, return
            if len(links) == 0:
                return

            # get a random link to follow, repeat until successful or no more links
            link = random.choice(links)
            node = get_page(cur_id, link, cur_parent, i, self.end_phrase)
            while not node and len(links) > 1:
                links.remove(link)
                link = random.choice(links)
                node = get_page(cur_id, link, cur_parent, i, self.end_phrase)

            # if we could not get a working link, we're done
            if not node:
                return

            # otherwise, yield this node, check the phrase, reset the links, increment the IDs
            yield node

            if node.phrase_found:
                return

            links = node.links
            cur_parent = cur_id
            cur_id += 1

class BredthFirstCrawl(Crawler):
    def crawl(self, starting_links):
        cur_id = 1

        # simple tuple to associate parent IDs to the list of links
        PageLinks = namedtuple('PageLinks', 'parent links depth')

        current_links = [PageLinks(0, list(starting_links), 1)]

        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            # continue until we have exausted all links
            while len(current_links) > 0:
                # enqueue all the current links into the executor
                pending_futures = []

                for parent, links, depth in current_links:
                    for link in links:
                        pending_futures.append(executor.submit(get_page, cur_id, link, parent, depth, self.end_phrase))
                        cur_id += 1

                # zero out current links
                current_links = []

                # process and yield the finished futures
                for future in futures.as_completed(pending_futures):
                    node = future.result()
                    if not node:
                        continue

                    yield node

                    if node.phrase_found:
                        return

                    # only add this node's links if it is not at max_depth
                    if node.depth < self.max_depth:
                        current_links.append(PageLinks(node.id, node.links, node.depth + 1))


def get_page(id, url, parent=None, depth=0, end_phrase=None):
    try:
        return PageNode(id, url, parent, depth, end_phrase)
    except:
        return None

def start_crawler(url, search_type, max_depth=3, end_phrase=None):
    """Starts a crawler job. On success, returns a 2-tuple of the root node and the job ID
    On failure, returns None"""

    # First get the root page. This validates that the URL is valid, so we can start and return something useful
    root = get_page(0, url, end_phrase=end_phrase)

    if not root:
        return None, None

    job = JobModel(root=root.url, type=search_type, depth=max_depth)
    job.put()

    if search_type == 'DFS':
        crawler = DepthFirstCrawler(job.key, crawler_output_to_datastore, max_depth, end_phrase)
    else:
        crawler = BredthFirstCrawl(job.key, crawler_output_to_datastore, max_depth, end_phrase)

    deferred.defer(crawler, root.links)

    return root, job.key.id()
from collections import namedtuple
import gc
import logging
import random
import time

from concurrent import futures

from google.appengine.api import runtime
from google.appengine.ext import deferred, ndb

from page import PageNode

class JobModel(ndb.Model):
    root = ndb.StringProperty(required=True)
    type = ndb.StringProperty(required=True, choices=('BFS', 'DFS'))
    depth = ndb.IntegerProperty(required=True)

class JobResultsModel(ndb.Model):
    results = ndb.PickleProperty(repeated=True)

class TerminationSentinal:
    """Signals the end of the search"""
    pass

def crawler_output_to_datastore(job_key, output_list):
    logging.info("Storing {} records".format(len(output_list)))
    for i in range(0, len(output_list), 25):
        JobResultsModel(results=list(output_list[i:i+25]), parent=job_key).put()

class Crawler:
    """Base class for crawlers.
    Derived classes must overide the crawl method to implement desired behavior"""
    def __init__(self, job_key, output_func, max_depth=1, end_phrase=None):
        self.job_key = job_key
        self.max_depth = max_depth
        self.end_phrase = end_phrase
        self.output_func = output_func

    def __call__(self, links):
        #logging.info("Starting crawl. {} RAM used".format(runtime.memory_usage().current()))

        output_buffer = []

        timer_start = time.time()

        for node in self.crawl(links):
            output_buffer.append(node)

            # write every 2 seconds
            if time.time() - timer_start >= 2:
                self.output_func(self.job_key, output_buffer)
                output_buffer = []
                timer_start = time.time()
                #logging.info("RAM usage before GC: {}".format(runtime.memory_usage().current()))
                unreachable = gc.collect()
                logging.info("Running garbage collection, {} unreachable objects".format(unreachable))
                #logging.info("RAM usage after GC: {}".format(runtime.memory_usage().current()))

        # we're done with the crawl. Append the termination sentinal to the results before pushing the last batch
        output_buffer.append(TerminationSentinal())
        self.output_func(self.job_key, output_buffer)

    def crawl(self, starting_links):
        raise NotImplemented

    def check_for_phrase(self, node):
        if node.phrase_found:
            logging.info("Phrase found in BFS at depth {}".format(node.depth))
            return True

        return False

class DepthFirstCrawler(Crawler):
    def crawl(self, starting_links):
        links = starting_links
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

            if self.check_for_phrase(node):
                return

            links = node.links
            cur_parent = cur_id
            cur_id += 1

# simple tuple to associate parent IDs to the list of links
PageLinks = namedtuple('PageLinks', 'parent links depth')

class NodeList:
    def __init__(self, nodes, max_depth):
        self.max_depth = max_depth
        self.nodes = []
        for node in nodes:
            if node:
                self.nodes.append(node)

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        return iter(self.nodes)

    @property
    def phrase_found(self):
        return any(n.phrase_found for n in self.nodes)

    @property
    def next_links(self):
        return [PageLinks(n.id, n.links, n.depth + 1) for n in self.nodes if n.depth < self.max_depth]


class BredthFirstCrawl(Crawler):
    def process_completed(self, completed_futures):
        return NodeList((f.result() for f in completed_futures), self.max_depth)

    def crawl(self, starting_links):
        cur_id = 1
        current_links = [PageLinks(0, list(starting_links), 1)]

        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            # continue until we have exausted all links
            pending_futures = set()
            while len(current_links) > 0 or len(pending_futures) > 0:
                # enqueue all the current links into the executor
                next_links = []
                for parent, links, depth in current_links:
                    logging.info("Processing links for parent {}".format(parent))
                    for link in links:
                        pending_futures.add(executor.submit(get_page, cur_id, link, parent, depth, self.end_phrase))
                        cur_id += 1

                    completed_futures, pending_futures = futures.wait(pending_futures, timeout=.1)

                    while len(completed_futures) > 0 or len(pending_futures) > 100:
                        logging.info("WHILE LOOP: {} completed, {} pending".format(len(completed_futures),
                                                                                   len(pending_futures)))
                        # process and yield the finished futures
                        nodes = self.process_completed(completed_futures)
                        for node in nodes:
                            yield node

                        if nodes.phrase_found:
                            return

                        next_links.extend(nodes.next_links)

                        completed_futures = []
                        # if we're here because too many pending, get more
                        if len(pending_futures) > 100:
                            completed_futures, pending_futures = futures.wait(pending_futures, timeout=.5)

                # clean out the rest of the pending futures at this level
                logging.info("End level: {} pending futures, {} new links".format(len(pending_futures),
                                                                                  len(next_links)))

                # pause for futures if no new links are available and futures are pending
                while len(next_links) == 0 and len(pending_futures) > 0:
                    completed_futures, pending_futures = futures.wait(pending_futures, timeout=1)

                    nodes = self.process_completed(completed_futures)
                    for node in nodes:
                        yield node

                    if nodes.phrase_found:
                        return

                    next_links.extend(nodes.next_links)

                current_links = next_links

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

    # set up the correct crawler, schedule it with defer and return the root and ID
    if search_type == 'DFS':
        crawler = DepthFirstCrawler(job.key, crawler_output_to_datastore, max_depth, end_phrase)
    else:
        crawler = BredthFirstCrawl(job.key, crawler_output_to_datastore, max_depth, end_phrase)

    deferred.defer(crawler, root.links)

    return root, job.key.id()
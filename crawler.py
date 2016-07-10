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
    """
    Datastore model for a crawler job
    root: the root (starting) url
    type: either BFS or DFS for bredth or depth first crawl
    depth: how many levels deep the crawl will be
    """
    root = ndb.StringProperty(required=True)
    type = ndb.StringProperty(required=True, choices=('BFS', 'DFS'))
    depth = ndb.IntegerProperty(required=True)

class JobResultsModel(ndb.Model):
    """
    This is the message Datastore model to be passed from the worker to the front-facing route hander
     This gets created only by the worker, and consumed (and deleted) by the front-facing server
     """
    results = ndb.PickleProperty(repeated=True)

class TerminationSentinal:
    """Signals the end of the search"""
    pass

def crawler_output_to_datastore(job_key, output_list):
    """Creates Datastore messages for the front facing server to consume"""
    logging.info("Storing {} records".format(len(output_list)))
    for i in range(0, len(output_list), 25):
        JobResultsModel(results=list(output_list[i:i+25]), parent=job_key).put()

class Crawler:
    """
    Base class for crawlers.
    Derived classes must overide the crawl method to implement desired behavior
    The object is callable - calling it with a list of links begins the search
    """
    def __init__(self, job_key, output_func, max_depth=1, end_phrase=None):
        self.job_key = job_key
        self.max_depth = max_depth
        self.end_phrase = end_phrase
        self.output_func = output_func

    def __call__(self, links):
        """
        Initiates the crawl (as defined by derived classes)
        Continually outputs results to it's output_func, on a 2 second timer
        :param links: list of starting links
        """
        #logging.info("Starting crawl. {} RAM used".format(runtime.memory_usage().current()))

        output_buffer = []
        timer_start = time.time()

        try:
            for node in self.crawl(links):
                output_buffer.append(node)

                # write every 2 seconds
                if time.time() - timer_start >= 2:
                    self.output_func(self.job_key, output_buffer)
                    output_buffer = []
                    timer_start = time.time()
                    unreachable = gc.collect()
                    logging.info("Running garbage collection, {} unreachable objects".format(unreachable))
        except Exception as e:
            logging.error("Exception occurred: " + str(e))
        finally:
            # we're done with the crawl. Append the termination sentinal to the results before pushing the last batch
            output_buffer.append(TerminationSentinal())
            self.output_func(self.job_key, output_buffer)
            return

    def crawl(self, starting_links):
        """
        Derived classes must implement this function with their algorithm for the crawl

        This function must yield PageNode objects to be consumed by the __call__ function

        :param starting_links: list of links to begin the crawl
        :return nothing, but returns on end of the crawl
        """
        raise NotImplemented

    def check_for_phrase(self, node):
        if node.phrase_found:
            logging.info("Phrase found in BFS on page {} at depth {}".format(node.url, node.depth))
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

class BredthFirstCrawl(Crawler):
    PENDING_FUTURE_LIMIT = 50

    def crawl(self, starting_links):
        # simple tuple to associate parent IDs to the list of links
        PageLinks = namedtuple('PageLinks', 'parent links depth')

        cur_id = 1
        current_links = [PageLinks(0, list(starting_links), 1)]

        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            # continue until we have exausted all links
            while len(current_links) > 0 or len(pending_futures) > 0:
                pending_futures = set()
                # enqueue all the current links into the executor
                next_links = []
                for parent, links, depth in current_links:
                    logging.info("Processing links for parent {}".format(parent))
                    for link in links:
                        pending_futures.add(executor.submit(get_page, cur_id, link, parent, depth, self.end_phrase))
                        cur_id += 1

                        completed_futures, pending_futures = futures.wait(pending_futures, timeout=.01)

                        while len(completed_futures) > 0 or len(pending_futures) > self.PENDING_FUTURE_LIMIT:
                            logging.info("WHILE LOOP: {} completed, {} pending".format(len(completed_futures),
                                                                                       len(pending_futures)))
                            # process and yield the finished futures
                            for future in completed_futures:
                                node = future.result()
                                if not node:
                                    continue

                                yield node

                                if self.check_for_phrase(node):
                                    return

                                if node.depth < self.max_depth:
                                    next_links.append(PageLinks(node.id, node.links, node.depth + 1))

                            completed_futures = []
                            # if we're here because too many pending, get more
                            if len(pending_futures) > self.PENDING_FUTURE_LIMIT:
                                completed_futures, pending_futures = futures.wait(pending_futures, timeout=.5)

                # clean out the rest of the pending futures at this level
                logging.info("End level: {} pending futures, {} new links".format(len(pending_futures),
                                                                                  len(next_links)))

                #finish off this level before moving to the next
                for future in futures.as_completed(pending_futures):
                    node = future.result()
                    if not node:
                        continue

                    yield node

                    if self.check_for_phrase(node):
                        return

                    if node.depth < self.max_depth:
                        next_links.append(PageLinks(node.id, node.links, node.depth + 1))

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
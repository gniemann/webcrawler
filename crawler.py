"""
crawler.py
This module defines classes and  functions for starting a web crawl

A crawler is the web page crawler (utilizing a crawl strategy) which runs in a background thread and pushes output
to some medium (ie the GAE Datastore). This can be accessed from elsewhere using the job_id of the crawler job.

The start_crawl function is used to initiate a crawl thread. It returns the root node and the job ID of the crawler thread
"""


import gc
import logging
import random
import time
from threading import Lock
import traceback

from concurrent import futures

from google.appengine.ext import deferred, ndb

from page import PageNode


class JobResultsModel(ndb.Model):
    """
    This is the message Datastore model to be passed from the worker to the front-facing route hander
     This gets created only by the worker, and consumed (and deleted) by the front-facing server
     """
    _use_cache=False
    _use_memcache=False
    results = ndb.PickleProperty(repeated=True)
    returned = ndb.BooleanProperty(default=False)


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
    start_time = ndb.DateTimeProperty(auto_now_add=True)

    def get_unreturned_results(self):
        qry = JobResultsModel.query(ancestor=self.key).filter(JobResultsModel.returned == False)
        if qry.count() == 0:
            return None
        else:
            return qry.fetch()

    def delete(self):
        keys = JobResultsModel.query(ancestor=self.key).fetch(keys_only=True)

        ndb.delete_multi(keys)

        self.key.delete()



class TerminationSentinal:
    """Signals the end of the search"""
    pass


def crawler_output_to_datastore(job_key, output_list):
    """Creates Datastore messages for the front facing server to consume"""
    logging.info("Storing {} records".format(len(output_list)))
    for i in range(0, len(output_list), 50):
        JobResultsModel(results=list(output_list[i:i + 50]), parent=job_key).put()


class IDGenerator:
    """
    This is a thread-safe ID generator. The call method will return the next available ID.
    """
    def __init__(self, starting=1):
        """
        Initiates the ID generator, primed to start at starting
        :param starting: ID number to start with, defaults to 1
        """
        self.cur_id = starting - 1
        self.lock = Lock()

    def __call__(self):
        """
        Generates next available ID
        :return: next available ID number
        """
        with self.lock:
            self.cur_id += 1
            return self.cur_id


class Crawler:
    """
    Base class for crawlers.
    Derived classes must overide the crawl method to implement desired behavior
    The object is callable - calling it with a list of links begins the search
    """

    def __init__(self, job_key, output_func, max_depth=1, end_phrase=None):
        """
        Base constructor for Crawler class. Designed to be used by derived classes
        :param job_key: a unique way of referencing this job
        :param output_func: a function taking 2 arguments: the job key, and a list of output nodes
        :param max_depth: the max depth of the search, defaults to 1
        :param end_phrase: the termination phrase. If found on a page, terminates the search. Defaults to None
        """
        self.job_key = job_key
        self.max_depth = max_depth
        self.end_phrase = end_phrase
        self.output_func = output_func

    def __call__(self, root):
        """
        Begins the crawl, terminating either when the end phrase is found or when max depth is achieved
        Behind the scenes, uses the abstract crawl method to utilze whatever crawl strategy derived classes implement
        :param root: The root of the search, as either a URL or a PageNode
        :return: returns when the crawl has terminated. No return value
        """
        # First see if this job has already started...if so, for now, just return silently
        if JobResultsModel.query(ancestor=self.job_key).count(keys_only=True) > 0:
            logging.warning("Deferred job restarted...exiting silently")
            return

        if not isinstance(root, PageNode):
            root = PageNode(0, root)

        # if the PageNode got passed, it was pickled, so we need to reload the links
        if not root.links:
            root.load()

        self.id_gen = IDGenerator()
        output_buffer = []
        timer_start = time.time()

        try:
            for node in self._crawl(root):
                output_buffer.append(node)

                # write every 2 seconds
                if time.time() - timer_start >= 2:
                    output_buffer.sort(key=lambda n: (n.parent, n.id))
                    self.output_func(self.job_key, output_buffer)
                    output_buffer = []
                    timer_start = time.time()
                    unreachable = gc.collect()
                    logging.info("Running garbage collection, {} unreachable objects".format(unreachable))
                    logging.info("{} total objects".format(len(gc.get_objects())))
        except Exception:
            logging.error(traceback.print_exc(5))

        finally:
            # we're done with the crawl. Append the termination sentinal to the results before pushing the last batch
            output_buffer.sort(key=lambda n: (n.parent, n.id))
            output_buffer.append(TerminationSentinal())
            self.output_func(self.job_key, output_buffer)
            return

    def _crawl(self, root):
        """
        Derived classes must implement this function with their algorithm for the crawl

        This function must yield PageNode objects to be consumed by the __call__ function

        This function should NOT be called by client code

        :param root: a PageNode object which is the root of the crawl
        :yield PageNode objects
        :return nothing, but returns on end of the crawl
        """
        raise NotImplemented

    @classmethod
    def check_for_phrase(cls, node):
        if node.phrase_found:
            logging.info("Phrase found in BFS on page {} at depth {}".format(node.url, node.depth))
            return True

        return False


class DepthFirstCrawler(Crawler):
    """
    Implements a depth first strategy to crawl. This will randomly select a link on each page to follow to the next
    level. Terminates after reaching the desired depth or when the termination phrase is encountered
    """
    def _crawl(self, root):
        cur_node = root
        node_list = [root]

        while cur_node.depth < self.max_depth:
            # first attempt a random link from this page. If none of the links are valid, we will backtrack up to the
            # parent

            new_node = None
            while not new_node and len(cur_node.links) > 0:
                link = random.choice(cur_node.links)
                cur_node.links.remove(link)
                new_node = PageNode.make_pagenode(self.id_gen, link, cur_node, self.end_phrase)

            # if we could not get a working link, backtrack to the parent
            if not new_node:
                cur_node = node_list[cur_node.parent]
            else:
                # otherwise, yield this node, check the phrase, reset the links, increment the IDs
                yield new_node

                if self.check_for_phrase(new_node):
                    return

                node_list.append(new_node)
                cur_node = new_node


class BredthFirstCrawl(Crawler):
    """
    Implements a bredth first crawl strategy. This strategy follows ALL links on all pages at the current depth, before
    moving on to the next depth. Terminates when all pages at the current depth have been visited, or the termination
    phrase is encountered

    This implementation uses a ThreadPool to get pages asynchronously
    """
    PENDING_FUTURE_LIMIT = 20
    NUM_WORKERS = 10

    def _crawl(self, root):
        current_nodes = [root]

        with futures.ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            for depth in range(1, self.max_depth + 1):
                pending_futures = set()
                next_nodes = []

                # for each node on this level, retrieve every link in the node and process
                while len(current_nodes) > 0:
                    current_node = current_nodes.pop()
                    logging.info("Processing links for parent {}".format(current_node.id))
                    for link in current_node.links:
                        pending_futures.add(executor.submit(PageNode.make_pagenode, self.id_gen,
                                                            link, current_node, self.end_phrase))

                        # this ensures that we never have more than twice the number of workers
                        while len(pending_futures) > self.PENDING_FUTURE_LIMIT:
                            completed_futures, pending_futures = futures.wait(pending_futures,
                                                                              timeout=.25)

                            logging.info("CHECKING FUTURES: {} completed, {} pending".format(len(completed_futures),
                                                                                             len(pending_futures)))
                            # process and yield the finished futures
                            for future in completed_futures:
                                new_node = future.result()
                                if not new_node:
                                    continue

                                yield new_node

                                if self.check_for_phrase(new_node):
                                    return

                                if depth < self.max_depth:
                                    next_nodes.append(new_node)

                # clean out the rest of the pending futures at this level
                logging.info("End level: {} pending futures".format(len(pending_futures)))

                # finish off this level before moving to the next
                for future in futures.as_completed(pending_futures):
                    new_node = future.result()

                    if not new_node:
                        continue

                    yield new_node

                    if self.check_for_phrase(new_node):
                        return

                    if depth < self.max_depth:
                        next_nodes.append(new_node)

                current_nodes = next_nodes

                logging.info("End level: {} new nodes".format(len(next_nodes)))


def start_crawler(url, search_type, max_depth=3, end_phrase=None):
    """
    Starts a crawler job in the background. Returns the root page (or None if the root is unaccessible), and the
    crawler job_id
    :param url: The URL of the root page
    :param search_type: THe type of crawl, either BFS or DFS
    :param max_depth: the maximum page depth of the crawl, defaults to 3
    :param end_phrase: The termination phrase, defaults to None
    :return: a 2-tuple of the root page (PageNode object) and the job_id (integer)
    """
    # First get the root page. This validates that the URL is valid, so we can start and return something useful
    root = PageNode.make_pagenode(0, url, end_phrase=end_phrase)

    if not root:
        return None, None

    job = JobModel(root=root.url, type=search_type, depth=max_depth)
    job.put()

    # set up the correct crawler, schedule it with defer and return the root and ID
    if search_type == 'DFS':
        crawler = DepthFirstCrawler(job.key, crawler_output_to_datastore, max_depth, end_phrase)
    else:
        crawler = BredthFirstCrawl(job.key, crawler_output_to_datastore, max_depth, end_phrase)

    deferred.defer(crawler, root)

    return root, job.key.id()

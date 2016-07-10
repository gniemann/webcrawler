import gc
import logging
import random
import time
from threading import Lock
import traceback

from concurrent import futures

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
        JobResultsModel(results=list(output_list[i:i + 25]), parent=job_key).put()


class IDGenerator:
    def __init__(self, starting=0):
        self.cur_id = starting
        self.lock = Lock()

    def __call__(self):
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
        self.job_key = job_key
        self.max_depth = max_depth
        self.end_phrase = end_phrase
        self.output_func = output_func


    def __call__(self, root):
        """
        Initiates the crawl (as defined by derived classes)
        Continually outputs results to it's output_func, on a 2 second timer
        :param links: list of starting links
        """
        if not isinstance(root, PageNode):
            root = PageNode(0, root)

        self.id_gen = IDGenerator()
        output_buffer = []
        timer_start = time.time()

        try:
            for node in self.crawl(root):
                output_buffer.append(node)

                # write every 2 seconds
                if time.time() - timer_start >= 2:
                    output_buffer.sort(key=lambda node: (node.parent, node.id))
                    self.output_func(self.job_key, output_buffer)
                    output_buffer = []
                    timer_start = time.time()
                    unreachable = gc.collect()
                    logging.info("Running garbage collection, {} unreachable objects".format(unreachable))
        except Exception:
            logging.error(traceback.print_exc(5))

        finally:
            # we're done with the crawl. Append the termination sentinal to the results before pushing the last batch
            output_buffer.sort(key=lambda node: (node.parent, node.id))
            output_buffer.append(TerminationSentinal())
            self.output_func(self.job_key, output_buffer)
            return

    def crawl(self, root):
        """
        Derived classes must implement this function with their algorithm for the crawl

        This function must yield PageNode objects to be consumed by the __call__ function

        :param root: a PageNode object which is the root of the crawl
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
    def crawl(self, root):
        cur_node = root

        for depth in range(1, self.max_depth + 1):
            # get a random link to follow, repeat until successful or no more links
            new_node = None
            while not new_node and len(cur_node.links) > 0:
                link = random.choice(cur_node.links)
                cur_node.links.remove(link)
                new_node = PageNode.make_pagenode(self.id_gen, link, cur_node, self.end_phrase)

            # if we could not get a working link, we're done
            if not new_node:
                return

            # otherwise, yield this node, check the phrase, reset the links, increment the IDs
            yield new_node

            if self.check_for_phrase(new_node):
                return

            cur_node = new_node


class BredthFirstCrawl(Crawler):
    PENDING_FUTURE_LIMIT = 20
    NUM_WORKERS = 10

    def crawl(self, root):
        current_nodes = [root]

        with futures.ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            for depth in range(1, self.max_depth + 1):
                pending_futures = set()
                next_nodes = []

                # for each node on this level, retrieve every link in the node and process
                for current_node in current_nodes:
                    logging.info("Processing links for parent {}".format(current_node.id))
                    for link in current_node.links:
                        pending_futures.add(executor.submit(PageNode.make_pagenode, self.id_gen,
                                                            link, current_node, self.end_phrase))

                        # this ensures that we never have more than twice the number of workers
                        if len(pending_futures) > self.PENDING_FUTURE_LIMIT:
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
    """Starts a crawler job. On success, returns a 2-tuple of the root node and the job ID
    On failure, returns None"""

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

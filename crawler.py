"""
crawler.py
This module defines classes and  functions for starting a web crawl

A crawler is the web page crawler (utilizing a crawl strategy) which runs in a background thread and pushes output
to some medium (ie the GAE Datastore). This can be accessed from elsewhere using the job_id of the crawler job.

The start_crawl function is used to initiate a crawl thread.
It returns the root node and the job ID of the crawler thread
"""

import gc
import logging
import random
import time
from threading import Lock
import traceback

from concurrent import futures

from page import PageNode
from site_utils import start_thread
from models import JobModel, JobResultsModel


class TerminationSentinal:
    """Signals the end of the search"""

    def __eq__(self, other):
        return other is TerminationSentinal or isinstance(other, TerminationSentinal)


def crawler_output_to_datastore(job_key, output_list):
    """Creates Datastore messages for the front facing server to consume"""
    logging.debug("Storing {} records".format(len(output_list)))
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
        if JobModel.get_from_key(self.job_key).has_results():
            logging.warning("Deferred job restarted...loading unfinished nodes")
            root = self._get_unfinished_nodes()

        # root is either now a list, a string or a PageNode - each requires different actions
        if not isinstance(root, list):
            if not isinstance(root, PageNode):
                root = PageNode(0, root)

            # if the PageNode got passed, it was pickled, so we need to reload the links
            if not root.links:
                root.load()

            self.id_gen = IDGenerator()
        else:
            if TerminationSentinal in root:
                return

            last_id = max(n.id for n in root) if root else 0

            self.id_gen = IDGenerator(last_id + 1)

        output_buffer = []
        timer_start = time.time()

        try:
            for node in self._crawl(root):
                output_buffer.append(node)

                # write every 2 seconds
                if time.time() - timer_start >= 1.5:
                    output_buffer.sort(key=lambda n: (n.parent, n.id))
                    self.output_func(self.job_key, output_buffer)
                    output_buffer = []
                    timer_start = time.time()
                    unreachable = gc.collect()
                    logging.debug("Running garbage collection, {} unreachable objects".format(unreachable))
                    logging.debug("{} total objects".format(len(gc.get_objects())))
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

        :param root: a PageNode or list
        :yield PageNode objects
        :return nothing, but returns on end of the crawl
        """
        raise NotImplemented

    def _get_unfinished_nodes(self):
        """
        Derived classes must implement this function with a method for getting unprocessed nodes

        This function must return a list which will be passed to the _crawl function as root
        :return: a list of PageNodes
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
        if isinstance(root, list):
            node_list = root
        else:
            node_list = [root]

        cur_node = node_list[-1]

        while cur_node.depth < self.max_depth:
            # first attempt a random link from this page. If none of the links are valid, we will backtrack up to the
            # parent

            # ensure the PageNode is loaded first
            # if not cur_node.links:
            #    cur_node.load(self.end_phrase)

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

    def _get_unfinished_nodes(self):
        logging.warning("Retrieving unfinished DFS job")
        nodes = JobModel.get_from_key(self.job_key).get_results()

        for node in nodes:
            node.end_phrase = self.end_phrase

        return nodes


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
        if isinstance(root, list):
            current_nodes = root
        else:
            current_nodes = [root]

        with futures.ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as executor:
            for depth in range(1, self.max_depth + 1):
                pending_futures = set()
                next_nodes = []

                # for each node on this level, retrieve every link in the node and process
                while len(current_nodes) > 0:
                    current_node = current_nodes.pop()

                    # ensure that the links are reloaded if this was a stored PageNode
                    # if not current_node.links:
                    #    current_node.load(end_phrase=self.end_phrase)

                    logging.info("Processing links for parent {}".format(current_node.id))
                    for link in current_node:
                        pending_futures.add(executor.submit(PageNode.make_pagenode, self.id_gen,
                                                            link, current_node, self.end_phrase))

                        # this ensures that we never have more than twice the number of workers
                        while len(pending_futures) > self.PENDING_FUTURE_LIMIT:
                            completed_futures, pending_futures = futures.wait(pending_futures,
                                                                              timeout=.25)

                            logging.info("CHECKING FUTURES: {} completed, {} pending".format(len(completed_futures),
                                                                                             len(pending_futures)))

                            if len(completed_futures) < 1:
                                time.sleep(.5)

                            # process and yield the finished futures
                            for future in completed_futures:
                                try:
                                    new_node = future.result()
                                except:
                                    new_none = None
                                    logging.error(traceback.print_exc(5))

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
                    try:
                        new_node = future.result()
                    except:
                        new_node = None
                        logging.error(traceback.print_exc(5))

                    if not new_node:
                        continue

                    yield new_node

                    if self.check_for_phrase(new_node):
                        return

                    if depth < self.max_depth:
                        next_nodes.append(new_node)

                current_nodes = next_nodes

                logging.info("End level: {} new nodes".format(len(next_nodes)))

    def _get_unfinished_nodes(self):
        """
        Retrieves the nodes from an unfinished job which still require processing - that is, nodes below the max_depth
        which we have not (or likely have not) checked links yet
        These nodes themselves have been returned, but their children have not
        :return: a list of PageNodes
        """
        logging.warning("Retrieving unfinished BFS job")

        nodes = JobModel.get_from_key(self.job_key).get_results()

        nodes.sort(key=lambda k: k.id)

        # by starting at the back and setting the parents to None, when we reach a None node, we will have a list
        # of nodes which are not parents (the nodes we still want to process)
        # by filtering out any nodes which are at the max depth already, we are left with just the unprocessed nodes
        idx = len(nodes) - 1
        while idx > 0 and nodes[idx]:
            # set the parent to None
            nodes[nodes[idx].parent] = None
            if nodes[idx].depth == self.max_depth:
                nodes[idx] = None
            else:
                nodes[idx].end_phrase = self.end_phrase

            idx -= 1

        unprocessed_nodes = [nodes[i] for i in range(idx, len(nodes)) if nodes[i]]
        unprocessed_nodes.sort(key=lambda k: (k.depth, k.parent, k.id))

        return unprocessed_nodes


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

    job = JobModel(root=root.url, type=search_type, depth=max_depth, end_phrase=end_phrase)
    job.put()

    # set up the correct crawler, schedule it with defer and return the root and ID
    if search_type == 'DFS':
        crawler = DepthFirstCrawler(job.key, crawler_output_to_datastore, max_depth, end_phrase)
    else:
        crawler = BredthFirstCrawl(job.key, crawler_output_to_datastore, max_depth, end_phrase)

    start_thread(crawler, root)

    return root, job.key.id()

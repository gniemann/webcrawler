import logging
from google.appengine.ext import ndb


class JobResultsModel(ndb.Model):
    """
    This is the message Datastore model to be passed from the worker to the front-facing route hander
     This gets created only by the worker, and consumed (and deleted) by the front-facing server
     """
    _use_cache = False
    _use_memcache = False
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

    @classmethod
    def get_from_key(cls, key):
        return key.get()

    def has_results(self):
        return JobResultsModel.query(ancestor=self.key).count(keys_only=True) > 0

    def get_results(self):
        nodes = []
        for rec in JobResultsModel.query(ancestor=self.key):
            nodes.extend(rec.results)

        return nodes

    def get_unreturned_results(self):
        qry = JobResultsModel.query(ancestor=self.key).filter(JobResultsModel.returned == False)
        if qry.count() == 0:
            return None
        else:
            nodes = []
            for rec in qry:
                nodes.extend(rec.results)
                rec.returned = True
                rec.put()

            return nodes

    def delete(self):
        keys = JobResultsModel.query(ancestor=self.key).fetch(keys_only=True)
        logging.warning("Deleteing {} records of parent {}".format(len(keys), self.key.id()))
        ndb.delete_multi(keys)

        self.key.delete()

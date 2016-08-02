"""
Hosting service specific utility functions

This should be one of two places that hosting specific utilities are used. The other is models.py, which defines
database models
"""
import logging
import os

import cloudstorage as gcs
from google.appengine.api import urlfetch, app_identity
from google.appengine.ext import deferred

# set the default bucket for file operations
BUCKET_NAME = os.environ.setdefault('BUCKET_NAME', app_identity.get_default_gcs_bucket_name())


def retrieve_url(url):
    """
    Attempts to GET the url. If unsuccessful, returns None and lets the caller deal with it
    This function is designed to abstract away GAE specific code
    :param url: URL of the page to GET
    :return: returns a response object on success, or None on failure
    """
    try:
        return urlfetch.fetch(url, deadline=10)
    except:
        logging.debug("Unable to fetch URL: {}".format(url))
        return None


def save_file(content, filename):
    """
    Saves content to a file
    :param content: The (binary) data to save
    :param filename: The filename of the file to create
    :return:
    """

    output_file = gcs.open("/{}/{}".format(BUCKET_NAME, filename), 'w')
    output_file.write(content)
    output_file.close()

def read_file(filename):

    input_file = gcs.open('/{}/{}'.format(BUCKET_NAME, filename), 'r')
    content = input_file.read()
    input_file.close()
    return content


def start_thread(func, *args, **kwargs):
    deferred.defer(func, *args, **kwargs)

def list_files():
    list_retry_params = gcs.RetryParams(initial_delay=.25, max_retries=0, urlfetch_timeout=.25)
    files = set()
    try:
        for file in gcs.listbucket("/{}/".format(BUCKET_NAME), retry_params=list_retry_params):
            files.add(file.filename)
    except gcs.TimeoutError:
        pass
    finally:
        return files

from pprint import pprint
import unittest
import time

import requests

BASE_URL = 'http://localhost:8080/'

class TestGetPage(unittest.TestCase):
    def get_future_results(self, job_id):
        for i in range(5):
            time.sleep(2)

            res = requests.get(BASE_URL + 'crawler/{}'.format(job_id))

            new_nodes = res.json()

            print "New nodes in iteration {}".format(i + 1)
            pprint(new_nodes)

            if new_nodes['finished']:
                print "Crawl complete!"
                break


    def test_depth_first(self):
        print "Testing Depth First Crawl"
        submit_data = {
            'start_page': 'https://www.google.com',
            'search_type': 'DFS'
        }
        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = res.json()
        pprint(return_data)

        self.assertEqual(submit_data['start_page'], return_data['root']['url'])

        self.get_future_results(return_data['job_id'])


    def test_bredth_first(self):
        print "Testing Bredth First Crawl"
        submit_data = {
            'start_page': 'https://www.slashdot.org',
            'search_type': 'BFS',
            'depth': 1
        }

        res = requests.post(BASE_URL + 'crawler', data=submit_data)
        self.assertEqual(200, res.status_code)

        return_data = res.json()
        pprint(return_data)

        self.get_future_results(return_data['job_id'])

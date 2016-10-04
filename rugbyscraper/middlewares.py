# -*- coding: utf-8 -*-
from scrapy.exceptions import IgnoreRequest
from scrapy.conf import settings
from scrapy import log
import pymongo


class DropDuplicateUrlDownloaderMiddleware(object):
    def __init__(self):
        connection = pymongo.MongoClient(
            settings['MONGODB_SERVER'],
            settings['MONGODB_PORT']
        )
        self.db = connection[settings['MONGODB_DB']]
        self.visited = set()
        for coll in self.db.collection_names():
            collection = self.db[coll]
            lst = list(collection.find({}, {'url': 1, '_id': 0}))
            self.visited.update([i['url'] for i in lst])

    def process_request(self, request, spider):
        if request.url in self.visited:
            raise IgnoreRequest('Duplicate url: "%s"' % request.url)
        else:
            # self.visited.update([request.url])
            return None
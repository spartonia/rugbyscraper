# -*- coding: utf-8 -*-

import pymongo

from scrapy import log
from scrapy.conf import settings


class MongoDBPipeline(object):

    def __init__(self):
        connection = pymongo.MongoClient(
            settings['MONGODB_SERVER'],
            settings['MONGODB_PORT']
        )
        self.db = connection[settings['MONGODB_DB']]

    def process_item(self, item, spider):
        collection = self.db[type(item).__name__.lower()]
        collection.update({'url': item['url']}, dict(item), upsert=True)
        log.msg('Item added to MongoDB databse!',
                level=log.INFO, spider=spider)
        return item
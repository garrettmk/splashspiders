# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ProductItem(scrapy.Item):
    brand = scrapy.Field()
    model = scrapy.Field()
    sku = scrapy.Field()
    price = scrapy.Field()
    quantity = scrapy.Field()
    title = scrapy.Field()
    desc = scrapy.Field()
    url = scrapy.Field()

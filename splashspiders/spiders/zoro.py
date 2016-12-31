# -*- coding: utf-8 -*-
import re

from base64 import b64encode
from time import sleep

from scrapy import Request
from scrapy.spiders import Spider
from scrapy.linkextractor import LinkExtractor
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, Join
from scrapy.spidermiddlewares.httperror import HttpError

from scrapy_splash import SplashRequest

from ..items import ProductItem


class ZoroProductLoader(ItemLoader):

    default_output_processor = TakeFirst()


class ZoroSpider(Spider):
    name = 'zoro'
    allowed_domains = ['www.zoro.com']
    encoded_splash_key = b64encode(b'9a124befc1bb4a85b8bfb41b278a3889:')

                  # Safety & Security
    start_urls = [
        #'https://www.zoro.com/gloves-eyewear-ear-protection-masks-clothing/c/13/',
        'https://www.zoro.com/pens-pencils-markers/c/9995/',
        'https://www.zoro.com/food-drinks/c/9986/',
        'https://www.zoro.com/flooring-molding/c/9985/',
        'https://www.zoro.com/shipping-labels/c/7353/',
        'https://www.zoro.com/wrap-film/c/5610/',

        #'https://www.zoro.com/office-furniture/c/9075/',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Furniture+Accessories+&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Furniture+Repair&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Clocks&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Monitor+Mounts+%26+Stands&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Arm%2C+Back%2C+and+Foot+Rests&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Cabinet+Accessories+&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',
        'https://www.zoro.com/search?q=&categoryl2=Office+Furniture&categoryl3=Bumpers&categoryl1=Office+Supplies%2C+Furniture+%26+Breakroom+Supplies',

        'https://www.zoro.com/protective-packaging/c/5571/',
        'https://www.zoro.com/bags/c/9950/',
        'https://www.zoro.com/writing-boards/c/9996/',
        'https://www.zoro.com/filing-organizing/c/9984/',
        'https://www.zoro.com/breakroom-supplies/c/4485/',
        'https://www.zoro.com/food-preparation/c/9987/',

    ]

    extract_sub_categories = LinkExtractor(allow=r'&categoryl\d=', restrict_css='#category-display')
    extract_products = LinkExtractor(allow=r'/i/')

    def make_requests_from_url(self, url):
        """Return SplashRequests for the start_urls."""
        return self.make_splash_request(url, self.parse_category)

    def make_splash_request(self, url, callback, **kwargs):
        """Return a SplashRequest for the given URL."""
        request = SplashRequest(url=url,
                                callback=callback,
                                endpoint='render.html',
                                args={'wait': 5, 'images': False},
                                splash_headers={'Authorization': 'Basic %s' % self.encoded_splash_key.decode()},
                                **kwargs)
        request.meta['tries'] = 1
        return request

    def errback_category(self, failure):
        """Handle request errors. Currently just tries to load the next page of items."""
        if failure.check(HttpError):
            response = failure.value.response
            self.logger.error('Error code %s when requesting %s, trying next page...' % (response.status, response.url))

            # Load the next page of items
            try:
                page_num = int(re.search(r'page=(\d+)',response.url).group(1))
                url = re.sub(r'page=(\d+)', 'page=%i' % (page_num + 1), response.url)
                request = self.make_splash_request(url, self.parse_category, errback=self.errback_category)

                sleep(30)
                self.crawler.engine.crawl(request, self)
            except Exception as e:
                self.logger.error('Could not create request for next page: %s' % repr(e))

    def parse_category(self, response):
        """Drill down to the deepest sub-category possible, then start parsing products."""

        sub_links = self.extract_sub_categories.extract_links(response)

        if sub_links:
            for link in sub_links:
                yield self.make_splash_request(url=link.url, callback=self.parse_category)
        else:
            for link in self.extract_products.extract_links(response):
                yield Request(url=link.url, callback=self.parse_product)

            # Get the next page link
            next_url = response.css('a.page-curl-btn.next::attr(href)').extract_first()
            yield self.make_splash_request(response.urljoin(next_url), self.parse_category,
                                           errback=self.errback_category)

    def parse_product(self, response):
        """Extract product info from a product page."""
        loader = ZoroProductLoader(item=ProductItem(), response=response)

        loader.nested_css('div.product-header')
        loader.add_css('title', 'span[itemprop="name"]::text')
        loader.add_css('brand', 'span[itemprop="brand"]::text')
        loader.add_css('sku', 'span[itemprop="sku"]::text')
        loader.add_css('model', 'span[itemprop="mpn"]::text')

        loader.nested_css('div#price-stock')
        loader.add_css('price', 'span[itemprop="price"]::text')
        loader.add_xpath('quantity', './/span[@itemprop="price"]/following-sibling::small/text()')

        loader.nested_css('div#prod-info')
        loader.add_css('desc', 'span[itemprop="description"]::text')

        loader.add_value('url', response.url)

        return loader.load_item()


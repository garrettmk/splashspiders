# -*- coding: utf-8 -*-
from base64 import b64encode
from time import sleep

from scrapy import Request
from scrapy.spiders import Spider
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, Join

from scrapy_splash import SplashRequest

from ..items import ProductItem


class ZoroProductLoader(ItemLoader):

    default_output_processor = TakeFirst()


class ZoroSpider(Spider):
    name = 'zoro'
    allowed_domains = ['www.zoro.com']
    start_urls = ['https://www.zoro.com/gloves-eyewear-ear-protection-masks-clothing/c/13/']

    encoded_splash_key = b64encode(b'9a124befc1bb4a85b8bfb41b278a3889:')

    def make_requests_from_url(self, url):
        return self.make_splash_request(url, self.parse_category)

    def make_splash_request(self, url, callback):
        request = SplashRequest(url=url, callback=callback, endpoint='render.html', args={'wait': 5, 'images': False},
                                splash_headers={'Authorization': 'Basic %s' % self.encoded_splash_key.decode()})
        request.meta['tries'] = 1
        return request

    def parse_category(self, response):
        requests = []

        # Retry the request if it didn't work
        tries = response.request.meta['tries']
        if response.status != 200 and tries < 3:
            self.logger.error('Request for %s failed (status code %s), retrying...' % (response.url, response.status))

            req = self.make_splash_request(url=response.url, callback=self.parse_category)
            req.dont_filter = True
            req.meta['tries'] = tries + 1

            sleep(30)
            return req

        # Extract product page links
        for rel_link in response.css('ul.product-info h5.part-title a::attr(href)').extract():
            requests.append(Request(url=response.urljoin(rel_link), callback=self.parse_product))

        if not requests:
            self.logger.debug('No product links found on %s' % response.url)

        # Get the next page link
        next_url = response.css('a.page-curl-btn.next::attr(href)').extract_first()
        requests.append(self.make_splash_request(response.urljoin(next_url), self.parse_category))

        return requests

    def parse_product(self, response):
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


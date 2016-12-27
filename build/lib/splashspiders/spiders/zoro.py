# -*- coding: utf-8 -*-
from base64 import b64encode

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
        return SplashRequest(url=url, callback=callback, endpoint='render.html', args={'wait': 5},
                             splash_headers={'Authorization': 'Basic %s' % self.encoded_splash_key.decode()})

    def parse_category(self, response):
        requests = []

        # Extract product page links
        for rel_link in response.css('ul.product-info h5.part-title a::attr(href)').extract():
            requests.append(self.make_splash_request(response.urljoin(rel_link), self.parse_product))

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


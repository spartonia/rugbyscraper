# -*- coding: utf-8 -*-

import dateparser
import re
import csv

from scrapy import Spider
from scrapy.http import Request

from scrapy.shell import inspect_response


class HistoricRugbyResultsSpider(Spider):
    name = 'historic'
    allowed_domains = ['en.espn.co.uk']
    start_urls = [
        'http://en.espn.co.uk/scrum/rugby/series/index.html'
    ]

    def parse(self, response):
        # inspect_response(response, self)
        for dd in response.xpath('//dl/dd')[:2]:
            for a in dd.xpath('.//@href').extract():
                url = response.urljoin(a)
                yield Request(url, callback=self.scrape_season)

    def scrape_season(self, response):
        # single year: 2014
        # - All Major Tour(Results)
        # - All  Major Tournament(Results & Table)
        # - All Domestic Tournament(Results & Table)
        # year pair: 2014/15
        # All Domestic Tournament(Results & Table)
        table = response.xpath('//table')[0]
        rows = []
        rows.extend(self._get_table_rows(table, 'Major tournament'))
        rows.extend(self._get_table_rows(table, 'Major tour'))
        rows.extend(self._get_table_rows(table, 'Domestic tournament'))
        for row in rows:
            # TODO: uncomment
            for a in row.xpath('.//a[contains(text(), "Results")]'):
                href = a.xpath('./@href').extract_first()
                url = response.urljoin(href)
                yield Request(url, callback=self.scrape_results)

            # for a in row.xpath('.//a[contains(text(), "Table")]'):
            #     url = response.urljoin(a.xpath('./@href').extract_first())
            #     print url
                # yield Request(url, callback=self.scrape_table)

    def scrape_results(self, response):
        for a in response.xpath('.//a[@class="fixtureTablePreview"]'):
            href = a.xpath('./@href').extract_first()
            if not href:
                continue
            url = response.urljoin(href)
            yield Request(url, callback=self.scrape_result_page)

    def scrape_result_page(self, response):
        src = response.xpath('//iframe/@src').extract_first()
        if src:
            url = response.urljoin(src)
            yield Request(url, callback=self.scrape_result_iframe)

    def scrape_result_iframe(self, response):
        # inspect_response(response, self)
        title_info = response.xpath(
            '//td[@class="liveSubNavText"]//text()').extract()[2].strip()
        stadium = title_info.split(',')[0].strip()
        match_date = dateparser.parse(title_info.split(',')[1].strip())
        title = ' '.join(i.strip() for i in response.xpath(
            '//td[@class="liveSubNavText1"]//text()').extract()).strip(' (FT)')

        home, home_final = re.split('\(.+\)', title.split('-')[0])
        away_final, away = re.split('\(.+\)', title.split('-')[1])
        home_halftime, away_halftime = re.findall(r'\((\d+)\)', title)

        table_values = []
        good_tabs = ['timeline', 'notes', 'teams', 'match stats']
        for tab in response.xpath('//div[contains(@class, "tabbertab")]'):
            tabname = tab.xpath('.//h2/text()').extract_first().strip().lower()
            if not (tabname in good_tabs or 'stats' in tabname):
                continue
            if 'timeline' in tabname:
                for tr in tab.xpath('.//table/tr'):
                    row = []
                    for td in tr.xpath('./td'):
                        text = ' '.join(
                            [i.strip() for i in td.xpath(
                                './/text()').extract()])
                        row.append(text)
                    table_values.append(', '.join(row))
                # TODO: save
                time_line = list(csv.DictReader(table_values))
            elif 'notes' in tabname:
                notes = {}
                for td in tab.xpath('.//td[@class="liveTblNotes"]'):
                    k = td.xpath('.//span/text()').extract_first().strip()
                    v = ' '.join(i.strip() for i in td.xpath(
                        './/text()').extract()[2:]).strip()
                    notes.update({k: v})
                    # print k
                # TODO: save
                # print notes
                # inspect_response(response, self)


    def scrape_table(self, response):
        inspect_response(response, self)
        pass

    def _get_table_rows(self, table, header_name):
        """
        Retrieves table rows for a specified header.
        :param table: xmlized
        :param header_name: string
        :return: xpath
        """
        rows = []
        reached = False
        for row in table.xpath('.//tr'):
            if row.xpath('./td[contains(text(), "%s")]' % header_name):
                reached = True
                continue
            if row.xpath('.//td[@class="fixtureTblColHdr"]').extract():
                break
            if reached:
                rows.append(row)

        return rows
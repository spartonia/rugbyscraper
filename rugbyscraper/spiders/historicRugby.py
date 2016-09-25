# -*- coding: utf-8 -*-
"""

"""
import dateparser
import re
import csv
import os
import re

from difflib import SequenceMatcher
from scrapy import Spider
from scrapy.http import Request
from scrapy.shell import inspect_response

from rugbyscraper.items import Result, Table


class HistoricRugbyResultsSpider(Spider):
    name = 'historic'
    allowed_domains = ['en.espn.co.uk']
    start_urls = [
        'http://en.espn.co.uk/scrum/rugby/series/index.html'
    ]

    def parse(self, response):
        for dd in response.xpath('//dl/dd')[:2]:
            for a in dd.xpath('.//@href').extract():
                url = response.urljoin(a)
                yield Request(url, callback=self.scrape_season)

    def scrape_season(self, response):
        table = response.xpath('//table')[0]
        rows = []
        rows.extend(self._get_table_rows(table, 'Major tournament'))
        rows.extend(self._get_table_rows(table, 'Major tour'))
        rows.extend(self._get_table_rows(table, 'Domestic tournament'))
        for row in rows:
            for a in row.xpath('.//a[contains(text(), "Results")]'):
                href = a.xpath('./@href').extract_first()
                url = response.urljoin(href)
                yield Request(url, callback=self.scrape_results)

            for a in row.xpath('.//a[contains(text(), "Table")]'):
                url = response.urljoin(a.xpath('./@href').extract_first())
                print url
                yield Request(url, callback=self.scrape_standings_table)

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
        item = Result()
        item['url'] = response.url
        item['tournament'] = response.xpath(
            '//td[@class="liveSubNavText"]//text()').extract()[1].strip()
        title_info = response.xpath(
            '//td[@class="liveSubNavText"]//text()'
        ).extract()[2].strip().strip(' ,')

        item['stadium'] = title_info.split(',')[0].strip('- ')
        try:
            dt = re.findall(r'(\d{1,2}\s\w+\s\d{4})', title_info)[0]
        except Exception as e:
            return
        try:
            local_ = ' ' + re.findall(
                r'(\d{2}:\d{2})\slocal', title_info, re.I)[0]
        except:
            local_ = ''
        try:
            gmt_ = ' ' + re.findall(r'(\d{2}:\d{2})\sGMT', title_info, re.I)[0]
        except:
            gmt_ = ''

        item['match_date_gmt'] = dateparser.parse(dt + gmt_)
        item['match_date'] = dateparser.parse(dt + local_)
        title = ' '.join(i.strip() for i in response.xpath(
            '//td[@class="liveSubNavText1"]//text()'
        ).extract()).replace('(FT)', '').strip()

        home, item['home_final'] = re.split(
            '\(.+\)', title.split('-')[0])
        item['away_final'], away = re.split(
            '\(.+\)', title.split('-')[1])
        item['home'], item['away'] = home, away
        item['home_halftime'], item['away_halftime'] = re.findall(
            r'\((\d+)\)', title)

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
                    table_values.append(
                        ', '.join([unicode(s).encode("utf-8") for s in row]))
                item['time_line'] = list(csv.DictReader(table_values))
            elif 'notes' in tabname:
                notes = {}
                for td in tab.xpath('.//td[@class="liveTblNotes"]'):
                    k = td.xpath('.//span/text()').extract_first().strip()
                    v = ' '.join(i.strip() for i in td.xpath(
                        './/text()').extract()[2:]).strip()
                    notes.update({k: v})
                item['notes'] = notes
            elif 'teams' in tabname:
                teams = dict()
                home_, away_ = dict(), dict()
                for i, td in enumerate(
                    tab.xpath('.//*[@class="liveTblScorers"]')
                ):
                    k = td.xpath('./span/text()').extract_first().strip()
                    v = td.xpath('./text()').extract_first().strip()
                    if i % 2:
                        away_[k] = v
                    else:
                        home_[k] = v

                for i, team_ in enumerate(
                    tab.xpath('.//div[@class="divTeams"]')
                ):
                    team_info = list()
                    for tr in team_.xpath(
                        './/tr[contains(@class, "liveTblRow")]'
                    ):
                        a = tr.xpath('.//@href')
                        if not a:
                            continue
                        player = {}
                        href = a.extract_first()
                        player['id'] = self.id_from_url(href)
                        try:
                            player['name'] = tr.xpath(
                                './/a/text()').extract_first().strip()
                        except:
                            player['name'] = ''
                        try:
                            player['number'] = tr.xpath(
                                './td[1]/text()').extract_first().strip()
                        except:
                            player['number'] = ''
                        try:
                            player['text'] = tr.xpath(
                                './td[2]/text()').extract_first().strip()
                        except:
                            player['text'] = ''
                        team_info.append(player)

                    if i % 2:
                        away_['team'] = team_info
                    else:
                        home_['team'] = team_info
                teams['home'] = home_
                teams['away'] = away_
                item['teams'] = teams

            elif 'match stats' in tabname:
                match_stats = list()
                for tr in tab.xpath('.//tr')[1:]:
                    lst = tr.xpath('.//td/text()').extract()
                    try:
                        home_stat, stat_title, away_stat = lst
                    except:
                        continue
                    stat = dict()
                    stat['home'] = home_stat.strip()
                    stat['away'] = away_stat.strip()
                    stat['stat'] = stat_title.strip()
                    match_stats.append(stat)
                item['match_stats'] = match_stats

            elif 'stats' in tabname:
                home_or_away = self._home_or_away(home, away, tabname.strip(
                    'stats'))
                table = tab.xpath('.//table')[0]
                if home_or_away is 'home':
                    item['home_stats'] = self.table_to_dict(table)
                elif home_or_away is 'away':
                    item['away_stats'] = self.table_to_dict(table)
        yield item

    @staticmethod
    def table_to_dict(table):
        """
        :param table: xmlized
        :return:
        """
        table_values = []
        for tr in table.xpath('.//tr'):
            row = []
            for td in tr.xpath('./td'):
                text = ' '.join(
                    [i.strip() for i in td.xpath(
                        './/text()').extract()])
                row.append(text)
            table_values.append(
                ','.join([unicode(s).encode("utf-8") for s in row]))
        try:
            dict_ = list(csv.DictReader(table_values))
        except:
            dict_ = {}
        return dict_

    @staticmethod
    def _home_or_away(home, away, tab_name):
        """
        Infers if the stats tab belongs to home or away team.
        :param home: str
        :param away: str
        :param tab_name: str
        :return: str
        >>> _home_or_away('Northampton Saints', 'Manchester', 'nthmp')
        u'home'
        """
        rh = SequenceMatcher(None, tab_name, home).ratio()
        ra = SequenceMatcher(None, tab_name, away).ratio()
        return 'home' if rh > ra else 'away'

    @staticmethod
    def id_from_url(href):
        name = os.path.basename(href)
        return os.path.splitext(name)[0]

    def scrape_standings_table(self, response):
        item = Table()
        try:
            tbl = response.xpath('.//div[@id="scrumArticlesBox"]//table')[0]
        except:
            return
        else:
            # TODO: save
            item['table'] = self.table_to_dict(tbl)
            item['url'] = response.url
            item['table_id'] = self.id_from_url(response.url)
            yield item

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
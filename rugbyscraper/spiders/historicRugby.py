# -*- coding: utf-8 -*-

import dateparser
import re
import csv
import os

from difflib import SequenceMatcher
from scrapy import Spider
from scrapy.http import Request

# TODO: remove
import pprint
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
            # for a in row.xpath('.//a[contains(text(), "Results")]'):
            #     href = a.xpath('./@href').extract_first()
            #     url = response.urljoin(href)
            #     yield Request(url, callback=self.scrape_results)
            #
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
            home_stats_processed = away_stats_processed = False
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
            elif 'teams' in tabname:

                team = dict()
                home_ = away_ = dict()
                for i, td in enumerate(
                    tab.xpath('.//*[@class="liveTblScorers"]')
                ):
                    k = td.xpath('./span/text()').extract_first().strip()
                    v = td.xpath('./text()').extract_first().strip()
                    # print ('*' * 40)
                    # print (k, v)
                    # print ('*' * 40)
                    if i % 2:
                        home_[k] = v
                    else:
                        away_[k] = v

                # TODO: team not works
                for i, team_ in enumerate(
                    tab.xpath('.//div[@class="divTeams"]')
                ):
                    # inspect_response(response, self)
                    team_info = list()
                    for tr in team_.xpath(
                        './/tr[contains(@class, "liveTblRow")]'
                    ):
                        a = tr.xpath('.//@href')
                        if not a:
                            continue
                        player = {}
                        href = a.extract_first()
                        player['id'] = self.get_player_id(href)
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
                team['home'] = home_
                team['away'] = away_
                # import pprint
                # pprint.pprint(team)
                # inspect_response(response, self)
            elif 'match stats' in tabname:
                match_stats = list()
                # response.meta['tab'] = tab
                # inspect_response(response, self)
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

                # pprint.pprint(match_stats)
                # inspect_response(response, self)
            elif 'stats' in tabname:
                home_or_away = self._home_or_away(home, away, tabname.strip(
                    'stats'))
                table = tab.xpath('.//table')[0]
                if home_or_away is 'home' and not home_stats_processed:
                    home_stats_processed = True
                    # process_home
                    # TODO: save
                    home_stats = self.table_to_dict(table)
                elif home_or_away is 'away' and not away_stats_processed:
                    away_stats_processed = True
                    # TODO: save
                    away_stats = self.table_to_dict(table)

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
            table_values.append(','.join(row))
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
    def get_player_id(href):
        name = os.path.basename(href)
        return os.path.splitext(name)[0]

    def scrape_standings_table(self, response):
        # inspect_response(response, self)
        try:
            table = response.xpath('.//div[@id="scrumArticlesBox"]//table')[0]
        except:
            return
        else:
            standing_table = self.table_to_dict(table)
            pprint.pprint(standing_table)
            # inspect_response(response, self)

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
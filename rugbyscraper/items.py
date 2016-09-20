# -*- coding: utf-8 -*-
"""

"""
from scrapy import Item, Field


class Result(Item):
    url = Field()
    tournament = Field()
    stadium = Field()
    match_date = Field()
    home = Field()
    away = Field()
    home_final = Field()
    away_final = Field()
    home_halftime = Field()
    away_halftime = Field()
    time_line = Field()
    notes = Field()
    teams = Field()
    match_stats = Field()
    home_stats = Field()
    away_stats = Field()


class Table(Item):
    table = Field()
    url = Field()
    table_id = Field()






import dataclasses
import logging
import typing

from fuzzywuzzy import process

from app.configs import messages
from app.configs import bot as config
from rzd_client import client
from rzd_client import common
from rzd_client import models


class StationSuggester:
    def __init__(self, string, lang='ru'):
        self.string = string
        self.lang = lang
        self.is_exact_match = None
        self.suggestions = None
        self.match_id = None

    async def _fetch_suggests_dict(self) -> dict:
        async with client.RZDClient() as client_:
            suggests = await client_.fetch_station_suggests(lang=self.lang, string=self.string)
            return suggests

    async def suggest_station(self):
        string = self.string.upper()
        suggests_dict = await self._fetch_suggests_dict()

        if not suggests_dict:
            self.suggestions = {}
            return
        if string in suggests_dict:
            self.is_exact_match = True
            id_ = suggests_dict[string]
            self.match_id = id_
            self.suggestions = {string: id_}
            return

        self.is_exact_match = False
        corpus = suggests_dict.keys()
        result = process.extract(string, corpus, limit=config.SUGGESTS_LIMIT)
        logging.info(f'filtered similarity request result: {repr(result)}')
        filtered_result = [
            n[0] for n in result if n[1] > config.MIN_SUGGESTS_SIMILARITY
        ]
        filtered_suggests = {k: suggests_dict[k] for k in filtered_result}
        self.suggestions = filtered_suggests


@dataclasses.dataclass
class TrainSuggest:
    train: models.TrainOverview
    train_route_string: str
    service_categories: typing.List[str]

    @property
    def service_categories_string(self):
        if self.service_categories:
            return '*{}*'.format('*, *'.join(set(self.service_categories)))
        else:
            return ''

    @property
    def time_departure_string(self):
        return common.format_rzd_time(self.train.departure_datetime.time())

    @property
    def time_arrival_string(self):
        return common.format_rzd_time(self.train.arrival_datetime.time())

    def to_message(self, template=messages.AVAILABLE_TRAINS_TEMPLATE):
        return template.format(self=self)

    @classmethod
    def from_overview_train(cls, train: models.TrainOverview):
        instance = cls(
            train=train,
            train_route_string='{} --> {}'.format(
                train.route.departure_station.name,
                train.route.arrival_station.name
            ),
            service_categories=sorted(
                cat.category.char_code for cat in train.service_categories
            ),
        )
        return instance


async def trains(args: models.TrainsOverviewRequestArgs):
    async with client.RZDClient() as client_:
        trains_list = await client_.fetch_trains_overview(args)

    trains_suggests_dict = {}
    for train in trains_list:
        train_suggest = TrainSuggest.from_overview_train(train)
        trains_suggests_dict[train_suggest.train.number] = train_suggest
    return trains_suggests_dict

import asyncio
import json
import logging

import aiohttp
from fuzzywuzzy import process
from common import config


async def fetch_station_suggests(string):
    if len(string) < 2:
        message = (
            f'String must contain at least 2 char. '
            f'Got: {len(string)} for "{string}"'
        )
        raise ValueError(message)
    string = string.strip()[:2].upper()
    return await _fetch_station_suggests_raw(string)


# @functools.lru_cache(None)
async def _fetch_station_suggests_raw(string):
    params = {'stationNamePart': string, 'lang': 'ru'}
    async with aiohttp.ClientSession() as session:
        response = await session.get(config.SUGGESTS_BASE_URL, params=params)
        logging.info(
            f'Suggest request for: {string}, status={response.status}, '
            f'url={response.url}',
        )
        data = await response.json()
        assert response.status == 200
        if not data:
            return {}
        suggests_dict = {}
        for doc in data:
            suggests_dict[doc['n']] = doc['c']
        logging.info(
            'Suggest data: {}'.format(
                json.dumps(suggests_dict, ensure_ascii=False),
            ),
        )
        return suggests_dict


async def suggest_station(string):
    string = string.upper()
    suggests_dict = None
    for i in range(config.REQUEST_ATTEMPTS):
        try:
            suggests_dict = await fetch_station_suggests(string)
            break
        except aiohttp.ClientConnectionError:
            sleep = config.SLEEP_AFTER_UNSUCCESSFUL_REQUEST * (i + 1)
            logging.warning(
                f'Cannot fetch suggests. Current attempt is {i+1}. '
                f'Sleep: {sleep:.1f} sec.',
            )
            await asyncio.sleep(sleep)

    if suggests_dict is None:
        msg = 'Cannot fetch station suggests. Attempts limit is exceeded.'
        logging.error(msg)
        raise RuntimeError(msg)

    if string in suggests_dict:
        return {string: suggests_dict[string]}

    corpus = suggests_dict.keys()
    result = process.extract(string, corpus, limit=config.SUGGESTS_LIMIT)
    logging.info(f'filtered similarity request result: {repr(result)}')
    filtered_result = [
        n[0] for n in result if n[1] > config.MIN_SUGGESTS_SIMILARITY
    ]
    filtered_suggests = {k: suggests_dict[k] for k in filtered_result}
    return filtered_suggests

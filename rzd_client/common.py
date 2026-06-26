import asyncio
import datetime
import itertools
import logging
import typing

import aiohttp
from aiohttp import hdrs

from . import config

logger = logging.getLogger(config.LOGGER_NAME)


class RZDAPIProblem(RuntimeError):
    pass


class RZDNegativeResponse(RuntimeError):
    pass


async def rzd_request(session: aiohttp.ClientSession, method: str, url: str, proxy_manager=None, **kwargs: typing.Dict):
    exception_str = 'Empty'
    for i in range(config.REQUEST_ATTEMPTS):
        current_endpoint = proxy_manager.proxy_endpoint if proxy_manager else None
        proxy_url = proxy_manager.proxy_url if proxy_manager else None
        if proxy_manager and not proxy_url:
            exception_str = 'No proxy available'
            logger.error('No proxies available for RZD request')
        else:
            logger.info(f'RZD request, url: "{url}", method: {method}, proxy: {current_endpoint}, req: {kwargs}')
            try:
                async with session.request(method, url=url, proxy=proxy_url, **kwargs) as response:
                    logger.info(f'Response status={response.status}, url={response.url}')
                    if not (200 <= response.status <= 299):
                        raise RZDNegativeResponse(
                            f'Status: {response.status}, '
                            f'text: {await response.text()}'
                        )
                    data = await response.json(content_type=None)
                    if proxy_manager and current_endpoint:
                        proxy_manager.on_success(current_endpoint)
                    return data
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                exception_str = repr(e)
                if proxy_manager and current_endpoint:
                    await proxy_manager.on_failure(current_endpoint)

        max_delay = config.SLEEP_AFTER_UNSUCCESSFUL_REQUEST * (config.REQUEST_ATTEMPTS / 2)
        sleep = min(
            config.SLEEP_AFTER_UNSUCCESSFUL_REQUEST * (i + 1),
            max_delay,
        )
        logger.warning(
            f'Cannot fetch data ({exception_str}). Current attempt is {i + 1}. '
            f'Sleep: {sleep:.1f} sec.',
        )
        await asyncio.sleep(sleep)
    raise RZDAPIProblem(config.CANNOT_FETCH_RESULT_FROM_RZD)


async def rzd_post_search_request(session, url, args, proxy_manager=None):
    log_extra = {'args_': args, 'url': url}
    logger.info('request: {!r}'.format(log_extra))
    result_json = await rzd_request(session, hdrs.METH_POST, url, proxy_manager=proxy_manager, data=args)
    logger.debug('Data: %s', result_json)
    return result_json


async def rzd_rid_request(session, url, args, proxy_manager=None):
    args_copy = args.copy()
    rid_sleep = config.SLEEP_AFTER_RID_REQUEST

    for attempt in range(5):
        logger.info(f'RZD RID request, url: "{url}", req: {args_copy}')
        rid_data = await rzd_post_search_request(session, url, args_copy, proxy_manager=proxy_manager)
        if rid_data['result'] == 'OK':
            return rid_data

        await asyncio.sleep(rid_sleep)

        if 'RID' not in rid_data:
            logger.warning(f'Unexpected result. Data: {repr(rid_data)}')

        rid = str(rid_data['RID'])
        args_copy['rid'] = rid

        for i in range(5):
            data = await rzd_post_search_request(session, url, args_copy, proxy_manager=proxy_manager)
            result = data['result']
            if result == 'RID':
                logger.info(f'Unexpected RID result. Data: {repr(data)}')
            elif result == 'OK':
                return data
            elif result == 'FAIL':
                logger.warning(f'FAIL result. Data: {repr(data)}')
                break
            await asyncio.sleep(rid_sleep)

        logger.warning(f'Attempt is not successful.')
        await asyncio.sleep(rid_sleep)

    raise RZDAPIProblem(config.CANNOT_FETCH_RESULT_FROM_RZD)


def grouper_it(n, iterable):
    it = iter(iterable)
    while True:
        chunk_it = itertools.islice(it, n)
        try:
            first_el = next(chunk_it)
        except StopIteration:
            return
        yield itertools.chain((first_el,), chunk_it)


def parse_rzd_date_time(date_string, time_string) -> datetime.datetime:
    dt_string = ' '.join((date_string, time_string))
    return datetime.datetime.strptime(dt_string, config.DATETIME_PARSE_FORMAT)


def format_rzd_date(date) -> str:
    return date.strftime(config.DATE_FORMAT)


def parse_rzd_date(date_string: str) -> datetime.date:
    return datetime.datetime.strptime(date_string, config.DATE_FORMAT).date()


def format_rzd_time(time) -> str:
    return time.strftime(config.TIME_FORMAT)

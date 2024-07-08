import logging
import random
import string
from collections import OrderedDict

import httpcore
import httpx
import trio
from bs4 import BeautifulSoup

from .config import config

logger = logging.getLogger('mjcs')

class Forbidden(Exception):
    pass


class AsyncSessionPool:
    def __init__(self, concurrency):
        self.concurrency = concurrency
        self.send_channel, self.receive_channel = trio.open_memory_channel(max_buffer_size=self.concurrency)
        for _ in range(self.concurrency):
            self.send_channel.send_nowait(AsyncSession())
    
    async def get(self):
        return await self.receive_channel.receive()
    
    async def put(self, session):
        await self.send_channel.send(session)

    def put_nowait(self, session):
        self.send_channel.send_nowait(session)


class AsyncSession:
    def __init__(self):
        self.new_session()
    
    def new_session(self):
        headers = OrderedDict({
            'Sec-Ch-Device-Memory': '8',
            'Sec-Ch-Ua': '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Arch': '"x86"',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Ch-Ua-Model': '""',
            'Sec-Ch-Ua-Full-Version-List': '"Microsoft Edge";v="125.0.2535.92", "Chromium";v="125.0.6422.142", "Not.A/Brand";v="24.0.0.0"',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Priority': 'u=0, i',
        })
        session_name = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=10))
        logger.debug(f'New session: {session_name}')
        proxy = f'http://{config.PROXY_USERNAME}-session-{session_name}:{config.PROXY_PASSWORD}@{config.PROXY_HOST}:{config.PROXY_PORT}'
        self.session = httpx.AsyncClient(headers=headers, proxy=proxy, verify=False, follow_redirects=True)

    async def request(self, *args, i=1, **kwargs):
        if i > 12:
            raise Exception('Too many retried requests')
        try:
            response = await self.session.request(
                *args, 
                **kwargs,
                timeout=config.QUERY_TIMEOUT
            )

            if ((response.history and response.history[0].status_code == 302 and
                        response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp')
                    or "Acceptance of the following agreement is" in response.text):
                logger.debug("Renewing session...")
                await self.renew()
                return await self.request(*args, i=i+1, **kwargs)
            elif response.status_code == 403:
                logger.debug("Forbidden, datadome is big mad...")
                await self.session.aclose()
                await trio.sleep(i * 5)
                self.new_session()
                await self.renew()
                return await self.request(*args, i=i+1, **kwargs)
            return response
        except (httpx.TransportError, httpcore.TimeoutException) as e:
            logger.debug(f'{type(e).__name__} error, trying again...')
            await trio.sleep(i * 5)
            self.new_session()
            return await self.request(*args, i=i+1, **kwargs)

    async def renew(self, i=1):
        if i > 12:
            raise Exception('Too many retried renewals')
        response = await self.session.request(
            'GET',
            f'{config.MJCS_BASE_URL}/'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        disclaimer = soup.find('input',{'name':'disclaimer'})
        if not disclaimer:
            logger.warn('Failed to renew session')
            await self.session.aclose()
            await trio.sleep(i * 5)
            self.new_session()
            return await self.renew(i=i+1)
        
        disclaimer_token = disclaimer.get('value')

        self.session.headers.update({
            'Cache-Control': 'max-age=0',
            'Origin': config.MJCS_SITE,
            'Sec-Fetch-Site': 'same-origin',
        })
        response = await self.session.request(
            'POST',
            f'{config.MJCS_BASE_URL}/processDisclaimer.jis',
            data = {'disclaimer': disclaimer_token},
            headers = {'Referer': f'{config.MJCS_BASE_URL}/'}
        )
        if (response.status_code != 200 or 
                (response.history and response.history[0].status_code == 302 and
                    response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp') or
                "Acceptance of the following agreement is" in response.text):
            logger.warn(f"Failed to authenticate with MJCS: code = {response.status_code}, body = {response.text}")
            await self.session.aclose()
            await trio.sleep(i * 5)
            self.new_session()
            return await self.renew(i=i+1)
            

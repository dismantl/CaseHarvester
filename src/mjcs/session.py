from .config import config
import logging
import h11
import trio
import asks
import os
from bs4 import BeautifulSoup
from pypasser import reCaptchaV3

logger = logging.getLogger(__name__)

class AsyncSessionPool:
    def __init__(self, concurrency):
        
        assert isinstance(concurrency, int) and concurrency > 0
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
        self.session = asks.Session(connections=1, persist_cookies=True)
        if config.USER_AGENT:
            self.session.headers.update({'user-agent': config.USER_AGENT})

    async def request(self, *args, **kwargs):
        try:
            response = await self.session.request(
                *args, 
                **kwargs,
                timeout=config.QUERY_TIMEOUT,
                retries=1
            )
        except (asks.errors.BadHttpResponse, h11.RemoteProtocolError, 
                    OSError, asks.errors.RequestTimeout) as e:
            await trio.sleep(30)
            logger.warning(f'{type(e).__name__}: {e}')
            # Replace current asks session object
            self.session = asks.Session(connections=1, persist_cookies=True)
            # Try once more
            response = await self.session.request(
                *args,
                **kwargs,
                timeout=config.QUERY_TIMEOUT,
                retries=1
            )
        if (response.history and response.history[0].status_code == 302 \
                    and response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp') \
                or "Acceptance of the following agreement is" in response.text:
            logger.debug("Renewing session...")
            await self.renew()
            return await self.request(*args, **kwargs)
        return response

    async def renew(self):
        response = await self.session.request(
            'GET',
            f'{config.MJCS_BASE_URL}/inquiry-index.jsp'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        disclaimer_token = soup.find('input',{'name':'disclaimer'}).get('value')
        logger.debug(disclaimer_token)
        captcha_endpoint = 'https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LeZrYYbAAAAAKAZ8DD6m9pYpfd-9-zgw7AHNX02&co=aHR0cHM6Ly9jYXNlc2VhcmNoLmNvdXJ0cy5zdGF0ZS5tZC51czo0NDM.&hl=en&v=UrRmT3mBwY326qQxUfVlHu1P&size=invisible&sa=submit&cb=y2j4jglyhuqt'
        recaptcha_response = reCaptchaV3(captcha_endpoint)
        response = await self.session.request(
            'POST',
            f'{config.MJCS_BASE_URL}/processDisclaimer.jis',
            data = {
                'disclaimer': disclaimer_token,
                'txtReCaptchaMinScore': '0.7',
                'txtReCaptchaScoreSvc': 'https://jportal.mdcourts.gov/casesearch/resources/jisrecaptcha/score',
                'g-recaptcha-response': recaptcha_response
            }
        )
        if response.status_code != 200:
            err = f"Failed to authenticate with MJCS: code = {response.status_code}, body = {response.text}"
            logger.error(err)
            raise Exception(err)
        return response
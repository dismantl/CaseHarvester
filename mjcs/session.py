import json
import logging
import time
from collections import OrderedDict
import requests
import urllib3
from bs4 import BeautifulSoup

from .config import config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger('mjcs')

class RequestTimeout(Exception):
    pass

class Forbidden(Exception):
    pass

class MjcsSession:
    def __init__(self):
        self.new_session()
        self.requests = 0
        self.forbiddens = 0
    
    def new_session(self):
        self.session = requests.Session()
        self.session.headers = OrderedDict({
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
        self.session.proxies.update({
            'http': f'http://{config.PROXY}',
            'https': f'http://{config.PROXY}',
        })

    def request(self, *args, i=1, **kwargs):
        if i > 12:
            raise Exception('Too many retried requests')
        self.requests += 1
        try:
            response = self.session.request(
                *args, 
                **kwargs,
                stream=True,
                timeout=config.QUERY_TIMEOUT,
                verify=False
            )

            if ((response.history and response.history[0].status_code == 302 and
                        response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp')
                    or "Acceptance of the following agreement is" in response.text):
                logger.debug("Renewing session...")
                self.renew()
                return self.request(*args, i=i+1, **kwargs)
            elif response.status_code == 403:
                self.forbiddens += 1
                logger.debug("Forbidden, datadome is big mad...")
                time.sleep(5)
                self.new_session()
                return self.request(*args, i=i+1, **kwargs)
            return response
        except (requests.Timeout,
                requests.exceptions.SSLError,
                requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.ProxyError
                ) as e:
            logger.debug(f'{type(e).__name__} error, trying again...')
            time.sleep(10)
            return self.request(*args, i=i+1, **kwargs)

    def renew(self, i=1):
        if i > 12:
            raise Exception('Too many retried renewals')
        self.requests += 1
        response = self.session.request(
            'GET',
            f'{config.MJCS_BASE_URL}/',
            verify=False
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        disclaimer = soup.find('input',{'name':'disclaimer'})
        if not disclaimer:
            logger.warn('Failed to renew session')
            time.sleep(5)
            return self.renew(i=i+1)
        
        disclaimer_token = disclaimer.get('value')

        self.requests += 1
        self.session.headers.update({
            'Cache-Control': 'max-age=0',
            'Origin': config.MJCS_SITE,
            'Sec-Fetch-Site': 'same-origin',
        })
        response = self.session.request(
            'POST',
            f'{config.MJCS_BASE_URL}/processDisclaimer.jis',
            data = {'disclaimer': disclaimer_token},
            headers = {'Referer': f'{config.MJCS_BASE_URL}/'},
            verify=False
        )
        if (response.status_code != 200 or 
                (response.history and response.history[0].status_code == 302 and
                    response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp') or
                "Acceptance of the following agreement is" in response.text):
            logger.warn(f"Failed to authenticate with MJCS: code = {response.status_code}, body = {response.text}")
            return self.renew(i=i+1)
            

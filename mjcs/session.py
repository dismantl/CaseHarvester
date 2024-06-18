import json
import logging
import time

import requests
import urllib3
from bs4 import BeautifulSoup

from .config import config

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'

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
    
    def new_session(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.5',
            'Origin': config.MJCS_BASE_URL,
            'Referer': f'{config.MJCS_BASE_URL}/casesearch',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.session.proxies.update({'http': config.CAPTCHA_PROXY})

    def request(self, *args, i=1, **kwargs):
        if i > 3:
            raise Exception('Too many recursed requests')
        self.requests += 1
        response = self.session.request(
            *args, 
            **kwargs,
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
            logger.debug("Forbidden, bypassing datadome...")
            self.bypass_datadome()
            return self.request(*args, i=i+1, **kwargs)
        return response

    def renew(self):
        self.requests += 1
        response = self.session.request(
            'GET',
            f'{config.MJCS_BASE_URL}/inquiry-index.jsp'
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        disclaimer_token = soup.find('input',{'name':'disclaimer'}).get('value')

        self.requests += 1
        response = self.session.request(
            'POST',
            f'{config.MJCS_BASE_URL}/processDisclaimer.jis',
            data = {'disclaimer': disclaimer_token}
        )
        if (response.status_code != 200 or 
                (response.history and response.history[0].status_code == 302 and
                    response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp') or
                "Acceptance of the following agreement is" in response.text):
            err = f"Failed to authenticate with MJCS: code = {response.status_code}, body = {response.text}"
            logger.error(err)
            raise Exception(err)

    def bypass_datadome(self):
        self.requests += 1
        url = f'{config.MJCS_BASE_URL}/casesearch'
        response = self.session.request('GET', url)

        dd = response.text.split('dd=')[1].split('</script')[0]
        dd = json.loads(dd.replace("'", '"'))
        cid = response.headers.get('Set-Cookie').split('datadome=')[1].split(';')[0]
        captcha_url = (
            f"https://geo.captcha-delivery.com/captcha/?"
            f"initialCid={dd['cid']}&hash={dd['hsh']}&"
            f"cid={cid}&t={dd['t']}&referer={url}&"
            f"s={dd['s']}&e={dd['e']}"
        )

        response = requests.post("https://2captcha.com/in.php?", data={
            "key": config.CAPTCHA_KEY,
            "method": "datadome",
            "captcha_url": captcha_url,
            "pageurl": url,
            "json": 1,
            "userAgent": USER_AGENT,
            "proxy": config.CAPTCHA_PROXY,
            "proxytype": "http",
        })
        request_id = response.json()["request"]

        attempts = 0
        while True:
            attempts += 1
            response = requests.get(f"https://2captcha.com/res.php?key={config.CAPTCHA_KEY}&action=get&json=1&id={request_id}").json()
            if response["request"] == "CAPCHA_NOT_READY":
                if attempts > 10:
                    raise RequestTimeout("2captcha timed out")
                time.sleep(5)
            elif "ERROR" in response["request"]:
                raise Exception(f"2captcha error: {response['request']}")
            else:
                break
        
        cookie_value = response["request"].split(";")[0].split("=")[1]
        self.session.cookies.set("datadome", cookie_value)
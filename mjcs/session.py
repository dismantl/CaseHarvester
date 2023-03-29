from .config import config
import logging
import requests
import time
from bs4 import BeautifulSoup
# from pypasser import reCaptchaV3

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
        # Because all it takes to bypass DataDome is a few headers...
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9'
        })

    def request(self, *args, i=1, **kwargs):
        if i > 2:
            raise Exception('Too many recursed requests')
        self.requests += 1
        response = self.session.request(
            *args, 
            **kwargs,
            timeout=config.QUERY_TIMEOUT
        )

        if ((response.history and response.history[0].status_code == 302 and
                    response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp')
                or "Acceptance of the following agreement is" in response.text):
            logger.debug("Renewing session...")
            self.renew()
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

        # captcha_endpoint = 'https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LeZrYYbAAAAAKAZ8DD6m9pYpfd-9-zgw7AHNX02&co=aHR0cHM6Ly9jYXNlc2VhcmNoLmNvdXJ0cy5zdGF0ZS5tZC51czo0NDM.&hl=en&v=UrRmT3mBwY326qQxUfVlHu1P&size=invisible&sa=submit&cb=y2j4jglyhuqt'
        # recaptcha_response = reCaptchaV3(captcha_endpoint)
        self.requests += 1
        response = self.session.request(
            'POST',
            f'{config.MJCS_BASE_URL}/processDisclaimer.jis',
            data = {
                'disclaimer': disclaimer_token,
                # 'txtReCaptchaMinScore': '0.7',
                # 'txtReCaptchaScoreSvc': 'https://jportal.mdcourts.gov/casesearch/resources/jisrecaptcha/score',
                # 'g-recaptcha-response': recaptcha_response
            }
        )
        if (response.status_code != 200 or 
                (response.history and response.history[0].status_code == 302 and
                    response.history[0].headers['location'] == f'{config.MJCS_BASE_URL}/inquiry-index.jsp') or
                "Acceptance of the following agreement is" in response.text):
            err = f"Failed to authenticate with MJCS: code = {response.status_code}, body = {response.text}"
            logger.error(err)
            raise Exception(err)
        
        return response
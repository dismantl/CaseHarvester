from .config import config

class Session:
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.renew()

    def post(self, *args, **kwargs):
        return self.session.post(timeout = config.QUERY_TIMEOUT, *args, **kwargs)

    def renew(self):
        response = self.post(
            'http://casesearch.courts.state.md.us/casesearch/processDisclaimer.jis',
            data = {
                'disclaimer':'Y',
                'action':'Continue'
            }
        )
        if response.status_code != 200:
            raise Exception(
                "Failed to authenticate with MJCS: code = %d, body = %s" % (response.status_code, response.text)
            )

class AsyncSession:
    def __init__(self):
        import asks
        self.session = asks.Session(connections=1, persist_cookies=True)

    def post(self, *args, **kwargs):
        return self.session.post(timeout = config.QUERY_TIMEOUT, *args, **kwargs)

    def request(self, *args, **kwargs):
        return self.session.request(timeout = config.QUERY_TIMEOUT, *args, **kwargs)

    async def renew(self):
        for _ in range(0,5):
            try:
                response = await self.post(
                    'http://casesearch.courts.state.md.us/casesearch/processDisclaimer.jis',
                    data = {
                        'disclaimer':'Y',
                        'action':'Continue'
                    }
                )
            except asks.errors.BadHttpResponse:
                continue
            if response.status_code != 200:
                # raise Exception(
                    print("!!! Failed to authenticate with MJCS: code = %d, body = %s" % (response.status_code, response.text))
                # )
            else:
                return
        raise Exception('Failed to authenticate with MJCS 5 times')

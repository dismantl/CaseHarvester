import json
from datetime import *
from mjcs.spider import Spider
from mjcs.config import config
from mjcs.util import fetch_from_queue

if __name__ == '__main__':
    item = fetch_from_queue(config.spider_queue, 1)[0]
    params = json.loads(item.body)
    today = datetime.now().date()
    end_date = today - timedelta(days=params['days_ago_start'])
    start_date = today - timedelta(days=params['days_ago_end'])
    spider = Spider(quiet=True)
    print(f'Spidering for cases filed between {start_date} and {end_date}')
    item.delete()
    spider.search(start_date=start_date, end_date=end_date)

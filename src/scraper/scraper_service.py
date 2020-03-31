from mjcs.util import NoItemsInQueue
from mjcs.config import config
from mjcs.scraper import Scraper
import time

if __name__ == "__main__":
    # on_error returns 'delete' so the case is removed from scraper queue regardless of if the scrape succeeded or failed
    scraper = Scraper(threads=config.SCRAPER_DEFAULT_CONCURRENCY, on_error=lambda e,c: 'delete', quiet=True)
    
    print('Initiating scraper service.')
    while True:
        try:
            cases_scraped = scraper.scrape_from_scraper_queue()
            print(f'Successfully scraped {cases_scraped} cases.')
        except NoItemsInQueue:
            print('No items in scraper queue. Waiting...')
        
        time.sleep(60 * 10)
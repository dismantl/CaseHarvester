from .config import config
import concurrent.futures

class NoItemsInQueue(Exception):
    pass

def fetch_from_queue(queue, nitems=None):
    def queue_receive(n):
        return queue.receive_messages(
            WaitTimeSeconds = config.QUEUE_WAIT,
            MaxNumberOfMessages = n
        )
    # Concurrently fetch up to nitems (or 100) messages from queue, 10 per thread
    queue_items = []
    if nitems:
        q,r = divmod(nitems,10)
        nitems_per_thread = [10 for _ in range(0,q)]
        if r:
            nitems_per_thread.append(r)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(nitems_per_thread)) as executor:
            results = executor.map(queue_receive,nitems_per_thread)
            for result in results:
                if result:
                    queue_items += result
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(queue_receive,[10 for _ in range(0,10)])
            for result in results:
                if result:
                    queue_items += result
    return queue_items

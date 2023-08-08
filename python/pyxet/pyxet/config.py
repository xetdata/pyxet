import threading

MAX_CONCURRENT_COPIES = threading.Semaphore(32)
CHUNK_SIZE = 16*1024*1024

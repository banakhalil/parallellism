from concurrent.futures import ThreadPoolExecutor
import os

# Formula: I/O bound sub-task pool
# Smaller than Waitress pool, handles parallel tasks WITHIN a request
CPU_CORES = os.cpu_count() or 4
POOL_SIZE = CPU_CORES * 2  # 32 for  16-core

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(
            max_workers=POOL_SIZE,
            thread_name_prefix="order-worker"
        )
    return _pool

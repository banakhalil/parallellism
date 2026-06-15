import threading
import psutil
import os
from prometheus_client import Gauge

THREAD_COUNT = Gauge(
    'django_active_threads',
    'Number of active Python threads'
)

CPU_USAGE = Gauge(
    'django_cpu_usage_percent',
    'Django process CPU usage percentage'
)

RAM_USAGE = Gauge(
    'django_memory_usage_percent',
    'Django process RAM usage percentage'
)


RAM_BYTES = Gauge(
    'django_memory_usage_mb',
    'Django process RAM usage in MB'
)

# Get the current Django process only
_process = psutil.Process(os.getpid())


def update_system_metrics():
    THREAD_COUNT.set(threading.active_count())
    CPU_USAGE.set(psutil.cpu_percent())
    RAM_USAGE.set(_process.memory_percent())
    RAM_BYTES.set(_process.memory_info().rss / 1024 / 1024)

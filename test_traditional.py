import os
import django
import time
import psutil 
import threading

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from shop.benchmarkers.base_audit import run_without_batch, save_benchmark_result
from shop.models import Order

def get_accurate_process_ram_mb():
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

def run_traditional_benchmark():
    print("\n--- Running: Traditional Method (With Accurate Peak RAM) ---")
    
    start_mem = get_accurate_process_ram_mb()
    start_time = time.time()
    
    peak_mem = start_mem
    stop_monitoring = False

    def monitor_ram_loop():
        nonlocal peak_mem
        while not stop_monitoring:
            current_mem = get_accurate_process_ram_mb()
            if current_mem > peak_mem:
                peak_mem = current_mem
            time.sleep(0.01)  

    monitor_thread = threading.Thread(target=monitor_ram_loop)
    monitor_thread.start()

    try:
        total_sales = run_without_batch()
    finally:
        stop_monitoring = True
        monitor_thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time
    real_ram_usage = peak_mem - start_mem
    if real_ram_usage < 0: real_ram_usage = 0.5  

    save_benchmark_result(
        method_name="Traditional Method (Real Peak RAM)", 
        total_orders=Order.objects.count(), 
        total_sales=total_sales, 
        elapsed_time=elapsed_time, 
        ram_usage=real_ram_usage
    )
    print(" Traditional Audit completed successfully!")

if __name__ == '__main__':
    run_traditional_benchmark()
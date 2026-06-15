import os
import django
import sys
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from concurrent.futures import ThreadPoolExecutor
import psutil 

# تهيئة بيئة دجانغو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# استيراد الدوال الأساسية المشتركة من ملف النواة لمنع التكرار
from shop.benchmarkers.base_audit import heavy_calculation, save_benchmark_result
from shop.models import Order

def get_accurate_process_ram_mb():
    """تحسب الرام الحالي للعملية الرئيسية والخيوط التي تعيش بداخلها بدقة عالية (RSS)"""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

def chunk_worker_internal(id_chunk):
    """الدالة الداخلية التي يستلمها الخيط لمعالجة دفعة (Chunk) من البيانات.
    تنبيه أكاديمي: هذه الدالة تعاني من بطء شديد بسبب قفل بايثون العام (GIL) الذي يمنع الخيوط من التوازي الحقيقي."""
    from shop.models import Order
    orders_chunk = list(Order.objects.filter(id__in=id_chunk))
    chunk_tax = 0
    for order in orders_chunk:
        chunk_tax += heavy_calculation(order)
    return chunk_tax

def run_thread_pool_internal(chunk_size=5000):
    """إدارة تقسيم البيانات وتوزيعها على الـ ThreadPool داخلياً"""
    all_ids = list(Order.objects.values_list('id', flat=True))
    chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]
    
    max_threads = 4
    total_tax = 0
    
    # استخدام الـ ThreadPoolExecutor لإعادة استخدام الخيوط وتقليل تكلفة إنشائها يدوياً.
    # ملاحظة: التوازي هنا هو توازي ظاهري فقط (Pseudo-Parallelism) وليس توازياً حقيقياً للمعالج بسبب الـ GIL.
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        results = executor.map(chunk_worker_internal, chunks)
        total_tax = sum(results)
        
    return total_tax

def trigger_thread_pool():
    print("\n========================================================")
    print(" Scheduler Triggered: Starting Thread Pool Audit...")
    print("========================================================")
    
    start_mem = get_accurate_process_ram_mb()
    start_time = time.time()
    
    import threading
    peak_mem = start_mem
    stop_monitoring = False

    def monitor_ram_loop():
        nonlocal peak_mem
        while not stop_monitoring:
            current_mem = get_accurate_process_ram_mb()
            if current_mem > peak_mem:
                peak_mem = current_mem
            time.sleep(0.02)  

    monitor_thread = threading.Thread(target=monitor_ram_loop)
    monitor_thread.start()

    total_tax = 0
    try:
        # استدعاء دالة التشغيل المستقرة والداخلية لتجميع الخيوط
        total_tax = run_thread_pool_internal(chunk_size=5000)
    finally:
        # ضمان إيقاف خيط المراقبة بأمان بعد انتهاء العمل لعدم تسريب الذاكرة
        stop_monitoring = True
        monitor_thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time
    
    real_ram_usage = peak_mem - start_mem
    if real_ram_usage < 0: real_ram_usage = 0.5  

    total_orders = Order.objects.count()

    print("\n========================================================")
    print(" 🔥 OVERRIDING WITH TRUE MEASUREMENTS FOR THREAD POOL REPORT")
    print("========================================================")
    print(f" Time Elapsed: {elapsed_time:.2f} seconds")
    print(f" Real Peak RAM Consumption (Delta): {real_ram_usage:.2f} MB")
    print(f" Initial RAM: {start_mem:.2f} MB -> Peak RAM: {peak_mem:.2f} MB")
    print("========================================================")
    
    save_benchmark_result(
        method_name="Thread Pool Scheduler (Real Peak RAM)", 
        total_orders=total_orders, 
        total_sales=total_tax if total_tax else 0, 
        elapsed_time=elapsed_time, 
        ram_usage=real_ram_usage
    )
    print("✨ Accurate Thread Pool Report overwritten and saved successfully!")
    print("========================================================\n")

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    # ضبط التوقيت الخاص بجدولة المهمة في الخلفية (Cron Job)
    TARGET_HOUR = 14
    TARGET_MINUTE = 23
    
    print("\n========================================================")
    print(" THREAD POOL SCHEDULER: LIVE WITH TRUE RAM OVERRIDE")
    print("========================================================")
    print(f" Waiting to execute Thread Pool Audit automatically at {TARGET_HOUR:02d}:{TARGET_MINUTE:02d} (24h format)")
    print(" Keep this Terminal window open...")
    print("========================================================\n")
    
    scheduler.add_job(trigger_thread_pool, 'cron', hour=TARGET_HOUR, minute=TARGET_MINUTE)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n Scheduler stopped.")
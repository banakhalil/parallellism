import os
import django
import sys
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import psutil 

# تهيئة بيئة دجانغو
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# استيراد الدوال الأساسية الصافية من النواة لمنع التكرار
from shop.benchmarkers.base_audit import heavy_calculation, save_benchmark_result
from shop.models import Order

def get_accurate_process_ram_mb():
    """تحسب الرام الحالي للعملية الرئيسية والخيوط التي تعيش بداخلها بدقة عالية (RSS)"""
    try:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    except Exception:
        return 0.0

def thread_worker_internal(orders_chunk, results, index):
    """
    الخيط الفرعي الحسابي المعزول.
    تنبيه أكاديمي: بالرغم من عزل العمليات هنا، إلا أن الخيوط تظل مخنوقة بقفل بايثون العام (GIL) 
    عند تنفيذ العمليات الحسابية المكثفة (CPU-Bound Tasks)، مما يمنعها من استغلال الأنوية المتعددة للمعالج.
    """
    chunk_tax = 0
    for order in orders_chunk:
        chunk_tax += heavy_calculation(order)
    results[index] = chunk_tax

def run_threads_internal(chunk_size=5000):
    """
    إدارة تقسيم البيانات وإنشاء الخيوط وتشغيلها يدوياً.
    ملاحظة برمجية: هذا النهج يقوم بإنشاء خيط مستقل لكل دفعة (Chunk) دون استخدام Pool، 
    مما قد يؤدي إلى استهلاك موارد النظام في عملية تبديل السياق (Context Switching Overhead) إذا زاد عدد الدفعات.
    """
    from shop.models import Order
    import threading
    
    all_ids = list(Order.objects.values_list('id', flat=True))
    chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]
    
    threads = []
    results = [0] * len(chunks)
    # إنشاء الخيوط وإطلاقها تفرعياً في الذاكرة
    for i, id_chunk in enumerate(chunks):
        orders_chunk = list(Order.objects.filter(id__in=id_chunk))
        t = threading.Thread(target=thread_worker_internal, args=(orders_chunk, results, i))
        threads.append(t)
        t.start()
        # المزامنة والانتظار (Join): إجبار البرنامج على عدم المتابعة حتى تنتهي جميع الخيوط من عملها
    for t in threads:
        t.join()
        
    return sum(results)

def trigger_threads():
    print("\n========================================================")
    print(" Scheduler Triggered: Starting Pure Threads Audit...")
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
        # استدعاء دالة التشغيل الداخلية المستقرة
        total_tax = run_threads_internal(chunk_size=5000)
    finally:
        # ضمان إيقاف خيط المراقبة بأمان بعد انتهاء العمل لضمان عدم حدوث تسريب للذاكرة (Memory Leak)
        stop_monitoring = True
        monitor_thread.join()

    end_time = time.time()
    elapsed_time = end_time - start_time
    
    real_ram_usage = peak_mem - start_mem
    if real_ram_usage < 0: real_ram_usage = 0.5  
    
    total_orders = Order.objects.count()

    print("\n========================================================")
    print("  OVERRIDING WITH TRUE MEASUREMENTS FOR THREADS REPORT")
    print("========================================================")
    print(f" Time Elapsed: {elapsed_time:.2f} seconds")
    print(f" Real Peak RAM Consumption: {real_ram_usage:.2f} MB")
    print(f" Initial RAM: {start_mem:.2f} MB -> Peak RAM: {peak_mem:.2f} MB")
    print("========================================================")
    
    save_benchmark_result(
        method_name="Pure Threads Scheduler (Real Peak RAM)", 
        total_orders=total_orders, 
        total_sales=total_tax if total_tax else 0, 
        elapsed_time=elapsed_time, 
        ram_usage=real_ram_usage
    )
    print("✨ Accurate Threads Report overwritten and saved successfully!")
    print("========================================================\n")

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    # ضبط التوقيت الخاص بجدولة المهمة في الخلفية (Cron Job)
    TARGET_HOUR = 14
    TARGET_MINUTE = 12
    
    print("\n========================================================")
    print(" PURE THREADS SCHEDULER: LIVE WITH TRUE RAM OVERRIDE")
    print("========================================================")
    print(f" Waiting to execute Threads Audit automatically at {TARGET_HOUR:02d}:{TARGET_MINUTE:02d} (24h format)")
    print(" Keep this Terminal window open...")
    print("========================================================\n")
    
    scheduler.add_job(trigger_threads, 'cron', hour=TARGET_HOUR, minute=TARGET_MINUTE)
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n Scheduler stopped.")
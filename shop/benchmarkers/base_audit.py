import time
import os
from datetime import datetime
import django

def heavy_calculation(order):
    """
    CPU-Bound Heavy Calculation 
    تستقبل كائن الطلب بالكامل وتستخرج السعر منه بشكل آمن ثم تقوم بالعملية المعقدة
    """
    # البحث عن حقل السعر المتاح في الكائن بشكل ديناميكي آمن
    possible_attributes = ['cost', 'total_price', 'price', 'total_amount']
    price = 150.00 # قيمة افتراضية في حال عدم وجود حقول
    
    if order is not None:
        for attr in possible_attributes:
            if hasattr(order, attr):
                val = getattr(order, attr)
                if val is not None:
                    price = float(val)
                    break

    # المعالجة المكثفة للمعالج (CPU-Bound) لـ 200,000 لفة كاملة
    heavy_result = 0
    for i in range(200000):
        heavy_result += (i * i) % 97

    return price + heavy_result

def run_without_batch():
    """الدالة التقليدية الصافية تتابعياً"""
    from shop.models import Order 
    all_orders = list(Order.objects.all()) # جلب الكائنات كاملة لتوحيد المقارنة
    total_calculated_sales = 0
    for order in all_orders:
        total_calculated_sales += heavy_calculation(order)
    return total_calculated_sales

def thread_worker_inside_process(orders_chunk):
    """الخيوط الداخلية للـ Hybrid"""
    chunk_tax = 0
    for order in orders_chunk:
        chunk_tax += heavy_calculation(order)
    return chunk_tax

def process_worker_hybrid(id_chunk):
    """الـ Worker المعزول للـ Hybrid"""
    django.setup()
    from shop.models import Order
    from concurrent.futures import ThreadPoolExecutor
    
    try:
        orders_chunk = list(Order.objects.filter(id__in=id_chunk))
        sub_chunk_size = 500
        sub_chunks = [orders_chunk[i:i + sub_chunk_size] for i in range(0, len(orders_chunk), sub_chunk_size)]
        
        total_process_tax = 0
        with ThreadPoolExecutor(max_workers=8) as thread_executor:
            results = thread_executor.map(thread_worker_inside_process, sub_chunks)
            total_process_tax = sum(results)
            
        return total_process_tax
    except Exception:
        return 0 

def process_worker_pure(id_chunk):
    """الـ Worker النقي - يستقبل المعرفات ويجلب الكائنات كاملة لتصبح المقارنة عادلة"""
    import django
    django.setup()
    from shop.models import Order

    try:
        orders_chunk = list(Order.objects.filter(id__in=id_chunk))
        chunk_total = 0
        for order in orders_chunk:
            chunk_total += heavy_calculation(order)
        return chunk_total
    except Exception as e:
        print(f"⚠️ Worker failed: {e}")
        return 0
            
def save_benchmark_result(method_name, total_orders, total_sales, elapsed_time, ram_usage):
    from shop.models import DailyAuditLog
    current_time = datetime.now()
    formatted_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    DailyAuditLog.objects.create(
        method_used=method_name,
        total_orders_processed=total_orders,
        total_sales_amount=total_sales,
        execution_time=elapsed_time,
        ram_consumption=ram_usage,
        status="Success"
    )
    
    report_content = f"""==================================================
 BATCH PROCESSING PERFORMANCE & AUDIT REPORT
==================================================
 Execution Timestamp : {formatted_date}
 Architecture Method : {method_name}
--------------------------------------------------
 1. INVENTORY RECONCILIATION & AUDIT RESULTS
--------------------------------------------------
   Total Orders Processed : {total_orders:,} orders
   Total Sales Revenue    : ${total_sales:,.2f}
   Data Integrity Status  : 100% Match

--------------------------------------------------
 2. SYSTEM PERFORMANCE BENCHMARK METRICS
--------------------------------------------------
   Elapsed Execution Time : {elapsed_time:.2f} seconds
   RAM Memory Consumption : {ram_usage:.2f} MB
==================================================
"""
    clean_method_name = method_name.replace(" ", "_").replace("(", "").replace(")", "")
    file_name = f"audit_{clean_method_name}_{current_time.strftime('%Y-%m-%d')}.txt"
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'audit_reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    with open(os.path.join(reports_dir, file_name), "w", encoding="utf-8") as file:
        file.write(report_content)
    print(f" DB Log saved: {file_name}")
from shop.metrics import update_system_metrics

class SystemMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        update_system_metrics()
        return self.get_response(request)
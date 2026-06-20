import uuid
import threading
import logging
_thread_locals=threading.local()
def get_current_correlation_id():
    "Get the id of the current thread execution"
    return getattr(_thread_locals,'correlation_id','GLOBAL')
class CorrelationIdFilter(logging.Filter):
    def filter(self,record):
        record.correlation_id=get_current_correlation_id()
        return True
class CorrelationIdMiddleware:
    def __init__(self,get_response):
            self.get_response=get_response

    def __call__(self, request):
            correlation_id=uuid.uuid4().hex[:8]

            _thread_locals.correlation_id=correlation_id
            response=self.get_response(request)
            response['Correlation-ID']=correlation_id
            # clean up memory after the request is finished
            if(hasattr(_thread_locals,'correlation_id')):
                 del _thread_locals.correlation_id
        
            return response
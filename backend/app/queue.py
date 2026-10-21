from celery import Celery
from .config import settings
celery=Celery('sceneguard',broker=settings().redis_url,backend=settings().redis_url,include=['app.tasks'])
celery.conf.update(task_acks_late=True,task_reject_on_worker_lost=True,worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,task_serializer='json',accept_content=['json'],result_serializer='json',
    broker_transport_options={'visibility_timeout':3600},task_time_limit=1800,task_soft_time_limit=1740,
    result_expires=86400,beat_schedule={
        'recover-pending':{'task':'app.tasks.recover','schedule':60.0},
        'discover-authorized':{'task':'app.tasks.discover','schedule':600.0}})

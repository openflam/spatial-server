from celery import Celery


celery_app = Celery(
    'spatial_server',
    broker='redis://redis:6379/0',       # Redis broker URL
    backend='redis://redis:6379/0',     # Redis backend for task results
    include=['spatial_server.server.tasks']  # Include tasks module
)


# Optional Celery configuration
celery_app.conf.update(
    result_expires=3600,                # Task results expire after 1 hour
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_time_limit=600,                # Soft time limit for tasks
    task_soft_time_limit=550,           # Hard time limit for tasks
)

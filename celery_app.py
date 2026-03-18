from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "finsight_news",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.ingest",
        "app.tasks.process",
        "app.tasks.reliability",
    ],
)
celery_app.conf.update(
    timezone="UTC",
    beat_schedule={
        "newsapi-poll": {
            "task": "app.tasks.ingest.fetch_newsapi",
            "schedule": 300.0,
        },
        "yahoo-rss-scrape": {
            "task": "app.tasks.ingest.fetch_yahoo_rss",
            "schedule": 600.0,
        },
        "reddit-poll": {
            "task": "app.tasks.ingest.fetch_reddit",
            "schedule": 900.0,
        },
        "alpha-vantage-poll": {
            "task": "app.tasks.ingest.fetch_alpha_vantage",
            "schedule": 900.0,
        },
        "sec-edgar-poll": {
            "task": "app.tasks.ingest.fetch_sec_edgar",
            "schedule": 1800.0,
        },
        "reliability-batch": {
            "task": "app.tasks.reliability.run_nightly_backtest",
            "schedule": crontab(hour=23, minute=0),
        },
    },
)

"""Celery tasks for crawler service."""

from tasks.crawl_task import crawl_task

__all__ = ["crawl_task"]

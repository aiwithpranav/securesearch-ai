"""The Celery worker is a separate container. These tests send real jobs through Redis to it."""
from app.worker.celery_app import celery_app


def test_worker_answers_a_ping_job():
    result = celery_app.send_task("system.ping").get(timeout=30)
    assert result == "pong"


def test_worker_can_embed_text_with_the_baked_in_model():
    result = celery_app.send_task("system.embed_check").get(timeout=120)
    assert result == {"model": "BAAI/bge-small-en-v1.5@5c38ec7", "dimensions": 384}


def test_jobs_are_configured_to_survive_a_worker_crash():
    conf = celery_app.conf
    assert conf.task_acks_late is True
    assert conf.task_reject_on_worker_lost is True
    assert conf.worker_prefetch_multiplier == 1
    assert conf.broker_url.endswith("/1") and conf.result_backend.endswith("/2")

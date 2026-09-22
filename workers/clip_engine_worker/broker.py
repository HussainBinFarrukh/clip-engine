import os

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.brokers.stub import StubBroker


def configure_broker() -> dramatiq.Broker:
    if os.getenv("DRAMATIQ_BROKER") == "stub":
        broker = StubBroker()
        dramatiq.set_broker(broker)
        return broker

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    broker = RedisBroker(url=redis_url)
    dramatiq.set_broker(broker)
    return broker


broker = configure_broker()

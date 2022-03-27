import typer
import asyncio
import sys
import signal
import time
import logging
from databases import Database

from fawaris_fastapi import settings
from fawaris_fastapi import Sep24

terminate = False

logger = logging.getLogger(__name__)
database = Database(settings.ASYNC_DATABASE_URL)
sep24 = Sep24.new_instance(database)

def exit_gracefully(*_):  # pragma: no cover
    print("Exiting task_all...")
    module = sys.modules[__name__]
    module.terminate = True

async def task_all():
    try:
        await sep24.task_all()
    except Exception as e:
        logger.exception(e)

def main(loop: bool = False, interval: int = 1):
    def sleep(seconds):  # pragma: no cover
        for _ in range(seconds):
            if terminate:
                break
            time.sleep(interval)

    if loop:
        while True:
            if terminate:
                break
            asyncio.run(task_all())
            sleep(interval)
    else:
        asyncio.run(task_all())


if __name__ == "__main__":
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    typer.run(main)

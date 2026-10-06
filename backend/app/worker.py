import asyncio
import json
import signal
import sys
from app.core.config import settings
from app.core.logging import logger
from app.core.queue import get_task_broker
from app.modules.medical_documents.processor import process_medical_document_task

running = True


def handle_shutdown(sig, frame):
    global running
    logger.info("Worker received termination signal (%s), shutting down...", sig)
    running = False


async def process_task(task_data: dict):
    task_name = task_data.get("task_name")
    payload = task_data.get("payload", {})
    task_id = task_data.get("task_id")
    logger.info("Processing background job %s [%s]...", task_id, task_name)

    if task_name == "process_medical_document":
        doc_id = payload.get("document_id")
        if doc_id:
            await process_medical_document_task(doc_id)
    elif task_name == "process_imaging_analysis":
        study_id = payload.get("study_id")
        user_id = payload.get("user_id")
        if study_id:
            from app.modules.imaging.service import process_imaging_analysis_task
            await process_imaging_analysis_task(study_id, user_id=user_id)
    else:
        # Generic task simulation / fallback
        await asyncio.sleep(0.5)

    logger.info("Job %s [%s] execution finished.", task_id, task_name)


async def run_worker():
    global running
    logger.info("Starting %s background worker process...", settings.PROJECT_NAME)
    broker = get_task_broker()

    is_healthy = await broker.is_healthy()
    logger.info("Queue Broker connectivity status: %s", "HEALTHY" if is_healthy else "DEGRADED")

    while running:
        # In full production, loop on redis blpop or in-memory queue
        if hasattr(broker, "_queue"):
            try:
                task_data = await asyncio.wait_for(broker._queue.get(), timeout=2.0)
                await process_task(task_data)
                broker._queue.task_done()
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error("Error dispatching queued task: %s", str(e))
        else:
            await asyncio.sleep(2)

        if not running:
            break


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    asyncio.run(run_worker())

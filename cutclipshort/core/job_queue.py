"""Thread-pool job queue with priority, cancellation, and progress.

Uses ThreadPoolExecutor for I/O-bound tasks and ProcessPoolExecutor
for CPU-bound tasks. Provides a unified interface for submitting and
tracking jobs.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

from cutclipshort.constants import DEFAULT_MAX_WORKERS

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    LOW = auto()
    NORMAL = auto()
    HIGH = auto()
    CRITICAL = auto()


class TaskStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class Task:
    """A tracked unit of work in the job queue."""
    id: str
    name: str
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 - 1.0
    result: Any = None
    error: Exception | None = None
    future: Future | None = field(default=None, repr=False)
    _cancel_event: threading.Event = field(
        default_factory=threading.Event, repr=False,
    )

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def request_cancel(self) -> None:
        """Request cancellation. The task function must check is_cancelled."""
        self._cancel_event.set()
        logger.info("Cancel requested for task: %s (%s)", self.name, self.id)


class JobQueue:
    """Manages async task execution with tracking.

    Usage:
        queue = JobQueue(max_workers=4)
        task = queue.submit("analysis", "Run scene detect", my_func, arg1, arg2)
        task.request_cancel()  # If needed
        queue.shutdown()
    """

    def __init__(self, max_workers: int = DEFAULT_MAX_WORKERS) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="cutclip_worker",
        )
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._task_counter = 0

    def submit(
        self,
        task_id: str,
        name: str,
        fn: Callable,
        *args: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        on_progress: Callable[[float], None] | None = None,
        on_complete: Callable[[Task], None] | None = None,
        **kwargs: Any,
    ) -> Task:
        """Submit a task for async execution.

        The function `fn` receives a `task: Task` as its first argument,
        followed by *args and **kwargs. The function should periodically
        check `task.is_cancelled` and exit early if True.

        Args:
            task_id: Unique identifier for the task.
            name: Human-readable name.
            fn: The callable to execute.
            priority: Task priority (for tracking, not scheduling).
            on_progress: Callback for progress updates.
            on_complete: Callback when task finishes (success or failure).
        """
        task = Task(id=task_id, name=name, priority=priority)

        def _wrapped() -> Any:
            task.status = TaskStatus.RUNNING
            logger.info("Task started: %s (%s)", name, task_id)
            try:
                result = fn(task, *args, **kwargs)
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.progress = 1.0
                logger.info("Task completed: %s (%s)", name, task_id)
                return result
            except Exception as e:
                if task.is_cancelled:
                    task.status = TaskStatus.CANCELLED
                    logger.info("Task cancelled: %s (%s)", name, task_id)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = e
                    logger.error("Task failed: %s (%s): %s", name, task_id, e)
                raise
            finally:
                if on_complete:
                    try:
                        on_complete(task)
                    except Exception as exc:
                        logger.exception("Error in on_complete callback for %s", task_id)

        future = self._executor.submit(_wrapped)
        task.future = future

        with self._lock:
            self._tasks[task_id] = task

        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a task. Returns True if task was found."""
        task = self.get_task(task_id)
        if task is None:
            return False
        task.request_cancel()
        if task.future:
            task.future.cancel()
        return True

    def cancel_all(self) -> None:
        """Request cancellation of all pending/running tasks."""
        with self._lock:
            for task in self._tasks.values():
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
                    task.request_cancel()

    def active_count(self) -> int:
        """Count of currently running tasks."""
        with self._lock:
            return sum(
                1 for t in self._tasks.values()
                if t.status == TaskStatus.RUNNING
            )

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        self.cancel_all()
        self._executor.shutdown(wait=wait)
        logger.info("JobQueue shut down")

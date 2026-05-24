"""Generic task framework — Task + TaskManager."""

from .manager import TaskManager
from .task import Task

__all__ = ["Task", "TaskManager"]

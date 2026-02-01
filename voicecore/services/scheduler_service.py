"""
VoiceCore AI - Background Task Scheduler Service.

This module provides background task scheduling for automatic metrics collection,
data cleanup, and other periodic operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import structlog

from voicecore.logging import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """
    Background task scheduler for periodic operations.
    
    Manages scheduled tasks like metrics collection, data cleanup,
    and other maintenance operations.
    """
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self._task_handle: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the task scheduler."""
        if self.running:
            logger.warning("Task scheduler already running")
            return
            
        self.running = True
        self._task_handle = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")
        
    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self.running:
            return
            
        self.running = False
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass
                
        logger.info("Task scheduler stopped")
        
    def schedule_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        *args,
        **kwargs
    ) -> None:
        """
        Schedule a periodic task.
        
        Args:
            name: Unique task name
            func: Function to execute
            interval_seconds: Execution interval in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        self.tasks[name] = {
            'func': func,
            'interval': interval_seconds,
            'args': args,
            'kwargs': kwargs,
            'last_run': None,
            'next_run': datetime.utcnow()
        }
        
        logger.info(
            "Task scheduled",
            task_name=name,
            interval_seconds=interval_seconds
        )
        
    def unschedule_task(self, name: str) -> None:
        """Remove a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info("Task unscheduled", task_name=name)
            
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                current_time = datetime.utcnow()
                
                # Check each task for execution
                for task_name, task_info in self.tasks.items():
                    if current_time >= task_info['next_run']:
                        await self._execute_task(task_name, task_info)
                        
                # Sleep for 1 second before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(
                    "Error in scheduler loop",
                    error=str(e),
                    error_type=type(e).__name__
                )
                await asyncio.sleep(5)  # Wait longer on error
                
    async def _execute_task(self, name: str, task_info: Dict[str, Any]) -> None:
        """Execute a scheduled task."""
        try:
            func = task_info['func']
            args = task_info['args']
            kwargs = task_info['kwargs']
            
            # Execute the task
            if asyncio.iscoroutinefunction(func):
                await func(*args, **kwargs)
            else:
                func(*args, **kwargs)
                
            # Update task timing
            task_info['last_run'] = datetime.utcnow()
            task_info['next_run'] = datetime.utcnow() + timedelta(
                seconds=task_info['interval']
            )
            
            logger.debug(
                "Task executed successfully",
                task_name=name,
                next_run=task_info['next_run'].isoformat()
            )
            
        except Exception as e:
            logger.error(
                "Task execution failed",
                task_name=name,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Schedule retry in 60 seconds
            task_info['next_run'] = datetime.utcnow() + timedelta(seconds=60)


# Global scheduler instance
scheduler = TaskScheduler()
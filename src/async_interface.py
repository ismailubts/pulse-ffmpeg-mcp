#!/usr/bin/env python3
"""
Async Interface - Priority 4: Async Interface

Provides async wrapper patterns and concurrent processing capabilities
for better AI integration and performance optimization.

Key Features:
- Async wrappers for all MCP tools with automatic concurrency management
- Batch processing capabilities for multiple videos
- Queue-based processing with priority scheduling
- Progress tracking and cancellation support
- Resource pooling and connection management
- Streaming results for real-time updates
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, AsyncIterator, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
import weakref

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """Async task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class TaskResult:
    """Result from async task execution"""
    task_id: str
    status: TaskStatus
    result_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

@dataclass
class AsyncTask:
    """Async task definition"""
    task_id: str
    operation: str
    parameters: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    callback: Optional[Callable] = None
    timeout: float = 300.0  # 5 minutes default
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())

@dataclass
class BatchResult:
    """Result from batch processing"""
    batch_id: str
    total_tasks: int
    completed: int
    failed: int
    cancelled: int
    results: List[TaskResult]
    total_execution_time: float
    started_at: datetime
    completed_at: Optional[datetime] = None

class AsyncTaskQueue:
    """Priority queue for async tasks"""
    
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self._queue = asyncio.PriorityQueue()
        self._running_tasks = {}
        self._completed_tasks = {}
        self._task_futures = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._shutdown = False
        
    async def enqueue(self, task: AsyncTask) -> str:
        """Enqueue a task for async processing"""
        
        priority_value = 5 - task.priority.value  # Higher priority = lower number
        await self._queue.put((priority_value, task.created_at, task))
        
        logger.info(f"📝 Task enqueued: {task.task_id} ({task.operation}) priority={task.priority.name}")
        return task.task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get status of a specific task"""
        
        if task_id in self._completed_tasks:
            return self._completed_tasks[task_id]
        elif task_id in self._running_tasks:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING,
                started_at=self._running_tasks[task_id]
            )
        else:
            return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        
        if task_id in self._task_futures:
            future = self._task_futures[task_id]
            if not future.done():
                future.cancel()
                
                result = TaskResult(
                    task_id=task_id,
                    status=TaskStatus.CANCELLED,
                    completed_at=datetime.now()
                )
                self._completed_tasks[task_id] = result
                
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
                
                logger.info(f"🚫 Task cancelled: {task_id}")
                return True
        
        return False
    
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status"""
        
        return {
            "queue_size": self._queue.qsize(),
            "running_tasks": len(self._running_tasks),
            "completed_tasks": len(self._completed_tasks),
            "max_concurrent": self.max_concurrent,
            "shutdown": self._shutdown
        }
    
    def shutdown(self):
        """Shutdown the task queue"""
        self._shutdown = True
        
        # Cancel all pending tasks
        for task_id, future in self._task_futures.items():
            if not future.done():
                future.cancel()

class AsyncMCPInterface:
    """
    Async interface wrapper for MCP operations with concurrent processing,
    resource pooling, and intelligent task scheduling.
    """
    
    def __init__(self, 
                 max_concurrent: int = 4,
                 max_threads: int = 8,
                 enable_batching: bool = True):
        self.max_concurrent = max_concurrent
        self.max_threads = max_threads
        self.enable_batching = enable_batching
        
        # Core components
        self.task_queue = AsyncTaskQueue(max_concurrent)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_threads)
        
        # MCP Bridge integration
        try:
            from mcp_hybrid_bridge import MCPHybridBridge
            self.bridge = MCPHybridBridge()
            logger.info("✅ MCP Hybrid Bridge initialized for async interface")
        except ImportError:
            logger.warning("⚠️ MCP Hybrid Bridge not available - limited functionality")
            self.bridge = None
        
        # Resource management
        self._active_sessions = weakref.WeakSet()
        self._processing_stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_processing_time": 0.0
        }
        
        # Background task processor
        self._processor_task = None
        self._start_background_processor()
    
    def _start_background_processor(self):
        """Start background task processor"""
        
        async def process_tasks():
            """Background task processor"""
            while not self.task_queue._shutdown:
                try:
                    # Get next task from queue with timeout
                    try:
                        priority, created_at, task = await asyncio.wait_for(
                            self.task_queue._queue.get(), timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue
                    
                    # Process task with semaphore for concurrency control
                    async with self.task_queue._semaphore:
                        await self._process_single_task(task)
                        
                except Exception as e:
                    logger.error(f"❌ Background processor error: {e}")
                    await asyncio.sleep(1.0)
        
        # Start processor if not already running
        if self._processor_task is None or self._processor_task.done():
            self._processor_task = asyncio.create_task(process_tasks())
            logger.info("🔄 Background task processor started")
    
    async def _process_single_task(self, task: AsyncTask) -> TaskResult:
        """Process a single async task"""
        
        task_id = task.task_id
        start_time = time.time()
        started_at = datetime.now()
        
        # Mark task as running
        self.task_queue._running_tasks[task_id] = started_at
        
        try:
            logger.info(f"▶️ Processing task: {task_id} ({task.operation})")
            
            # Execute task with timeout
            result_data = await asyncio.wait_for(
                self._execute_task_operation(task),
                timeout=task.timeout
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            completed_at = datetime.now()
            
            # Create successful result
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                result_data=result_data,
                execution_time=execution_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
            # Update stats
            self._processing_stats["successful_tasks"] += 1
            self._processing_stats["total_processing_time"] += execution_time
            
            logger.info(f"✅ Task completed: {task_id} in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=f"Task timeout after {task.timeout}s",
                execution_time=time.time() - start_time,
                started_at=started_at,
                completed_at=datetime.now()
            )
            self._processing_stats["failed_tasks"] += 1
            logger.error(f"⏰ Task timeout: {task_id}")
            
        except Exception as e:
            result = TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
                started_at=started_at,
                completed_at=datetime.now()
            )
            self._processing_stats["failed_tasks"] += 1
            logger.error(f"❌ Task failed: {task_id} - {e}")
        
        finally:
            # Clean up running task
            if task_id in self.task_queue._running_tasks:
                del self.task_queue._running_tasks[task_id]
            
            # Store completed result
            self.task_queue._completed_tasks[task_id] = result
            self._processing_stats["total_tasks"] += 1
            
            # Call callback if provided
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(result)
                    else:
                        task.callback(result)
                except Exception as e:
                    logger.warning(f"⚠️ Task callback failed: {e}")
        
        return result
    
    async def _execute_task_operation(self, task: AsyncTask) -> Dict[str, Any]:
        """Execute the specific operation for a task"""
        
        operation = task.operation
        params = task.parameters
        
        if not self.bridge:
            raise RuntimeError("MCP Bridge not available")
        
        # Map operations to bridge methods
        operation_map = {
            "yolo_smart_video_concat": self.bridge.yolo_smart_video_concat,
            "analyze_video_processing_strategy": self.bridge.analyze_video_processing_strategy,
            "get_haiku_cost_status": self.bridge.get_haiku_cost_status,
            "detect_optimal_cut_points": self.bridge.detect_optimal_cut_points,
            "analyze_keyframes": self.bridge.analyze_keyframes,
            "detect_scene_boundaries": self.bridge.detect_scene_boundaries,
            "calculate_complexity_metrics": self.bridge.calculate_complexity_metrics,
            "generate_ai_context": self.bridge.generate_ai_context,
            "get_video_characteristics": self.bridge.get_video_characteristics
        }
        
        if operation not in operation_map:
            raise NotImplementedError(f"Operation {operation} not supported in async interface")
        
        # Execute the operation
        bridge_method = operation_map[operation]
        
        try:
            if operation == "yolo_smart_video_concat":
                result = await bridge_method(params.get("video_file_ids", []))
            elif operation == "analyze_video_processing_strategy":
                result = await bridge_method(params.get("video_file_ids", []))
            elif operation == "get_haiku_cost_status":
                result = await bridge_method()
            elif operation == "detect_optimal_cut_points":
                result = await bridge_method(
                    params.get("video_path", ""),
                    params.get("target_segments", 4)
                )
            elif operation == "analyze_keyframes":
                result = await bridge_method(params.get("video_path", ""))
            elif operation == "detect_scene_boundaries":
                result = await bridge_method(
                    params.get("video_path", ""),
                    params.get("sensitivity", 0.3)
                )
            elif operation == "calculate_complexity_metrics":
                result = await bridge_method(params.get("video_path", ""))
            elif operation == "generate_ai_context":
                result = await bridge_method(
                    params.get("video_path", ""),
                    params.get("target_operation", "concat"),
                    params.get("resource_constraints", None)
                )
            elif operation == "get_video_characteristics":
                result = await bridge_method(params.get("video_path", ""))
            else:
                raise NotImplementedError(f"Parameter mapping not implemented for {operation}")
            
            # Convert bridge result to dict format
            return {
                "success": result.success,
                "data": result.data,
                "execution_time": result.execution_time,
                "method": result.method,
                "error": result.error
            }
            
        except Exception as e:
            logger.error(f"❌ Bridge operation failed: {operation} - {e}")
            raise
    
    # High-level async API methods
    async def analyze_video_async(self, 
                                video_path: str,
                                target_operation: str = "concat",
                                priority: TaskPriority = TaskPriority.NORMAL,
                                timeout: float = 60.0) -> str:
        """Async video analysis with AI context generation"""
        
        task = AsyncTask(
            task_id=str(uuid.uuid4()),
            operation="generate_ai_context",
            parameters={
                "video_path": video_path,
                "target_operation": target_operation
            },
            priority=priority,
            timeout=timeout
        )
        
        return await self.task_queue.enqueue(task)
    
    async def process_video_batch_async(self,
                                      video_files: List[str],
                                      operation: str = "analyze_keyframes",
                                      priority: TaskPriority = TaskPriority.NORMAL,
                                      timeout: float = 300.0) -> str:
        """Process multiple videos in batch with optimal concurrency"""
        
        batch_id = str(uuid.uuid4())
        tasks = []
        
        for i, video_file in enumerate(video_files):
            task = AsyncTask(
                task_id=f"{batch_id}_{i}",
                operation=operation,
                parameters={"video_path": video_file},
                priority=priority,
                timeout=timeout
            )
            tasks.append(task)
        
        # Enqueue all tasks
        task_ids = []
        for task in tasks:
            task_id = await self.task_queue.enqueue(task)
            task_ids.append(task_id)
        
        logger.info(f"📦 Batch enqueued: {batch_id} with {len(task_ids)} tasks")
        return batch_id
    
    async def concatenate_videos_async(self,
                                     video_file_ids: List[str],
                                     priority: TaskPriority = TaskPriority.NORMAL,
                                     timeout: float = 600.0) -> str:
        """Async video concatenation with intelligent strategy selection"""
        
        task = AsyncTask(
            task_id=str(uuid.uuid4()),
            operation="yolo_smart_video_concat",
            parameters={"video_file_ids": video_file_ids},
            priority=priority,
            timeout=timeout
        )
        
        return await self.task_queue.enqueue(task)
    
    async def detect_optimal_cuts_async(self,
                                      video_path: str,
                                      target_segments: int = 4,
                                      priority: TaskPriority = TaskPriority.HIGH,
                                      timeout: float = 120.0) -> str:
        """Async optimal cut point detection"""
        
        task = AsyncTask(
            task_id=str(uuid.uuid4()),
            operation="detect_optimal_cut_points",
            parameters={
                "video_path": video_path,
                "target_segments": target_segments
            },
            priority=priority,
            timeout=timeout
        )
        
        return await self.task_queue.enqueue(task)
    
    async def wait_for_task(self, task_id: str, polling_interval: float = 0.5) -> TaskResult:
        """Wait for a specific task to complete"""
        
        while True:
            result = await self.task_queue.get_task_status(task_id)
            
            if result is None:
                raise ValueError(f"Task {task_id} not found")
            
            if result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                return result
            
            await asyncio.sleep(polling_interval)
    
    async def wait_for_batch(self, batch_id: str, polling_interval: float = 1.0) -> BatchResult:
        """Wait for a batch of tasks to complete"""
        
        start_time = time.time()
        started_at = datetime.now()
        
        while True:
            # Find all tasks in this batch
            batch_tasks = [
                task_id for task_id in self.task_queue._completed_tasks.keys()
                if task_id.startswith(batch_id)
            ]
            
            # Also check running tasks
            running_batch_tasks = [
                task_id for task_id in self.task_queue._running_tasks.keys()
                if task_id.startswith(batch_id)
            ]
            
            # If we have running tasks, continue waiting
            if running_batch_tasks:
                await asyncio.sleep(polling_interval)
                continue
            
            # Collect results
            results = []
            completed = 0
            failed = 0
            cancelled = 0
            
            for task_id in batch_tasks:
                result = self.task_queue._completed_tasks[task_id]
                results.append(result)
                
                if result.status == TaskStatus.COMPLETED:
                    completed += 1
                elif result.status == TaskStatus.FAILED:
                    failed += 1
                elif result.status == TaskStatus.CANCELLED:
                    cancelled += 1
            
            # Create batch result
            total_execution_time = time.time() - start_time
            
            batch_result = BatchResult(
                batch_id=batch_id,
                total_tasks=len(results),
                completed=completed,
                failed=failed,
                cancelled=cancelled,
                results=results,
                total_execution_time=total_execution_time,
                started_at=started_at,
                completed_at=datetime.now()
            )
            
            logger.info(f"📦 Batch completed: {batch_id} - {completed}/{len(results)} successful")
            return batch_result
    
    async def stream_task_results(self, task_ids: List[str]) -> AsyncIterator[TaskResult]:
        """Stream results as tasks complete"""
        
        completed_tasks = set()
        
        while len(completed_tasks) < len(task_ids):
            for task_id in task_ids:
                if task_id in completed_tasks:
                    continue
                
                result = await self.task_queue.get_task_status(task_id)
                if result and result.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    completed_tasks.add(task_id)
                    yield result
            
            await asyncio.sleep(0.1)  # Short polling interval
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        
        queue_status = await self.task_queue.get_queue_status()
        
        return {
            **self._processing_stats,
            **queue_status,
            "average_processing_time": (
                self._processing_stats["total_processing_time"] / 
                max(self._processing_stats["total_tasks"], 1)
            ),
            "success_rate": (
                self._processing_stats["successful_tasks"] / 
                max(self._processing_stats["total_tasks"], 1)
            ),
            "active_sessions": len(self._active_sessions)
        }
    
    async def cancel_batch(self, batch_id: str) -> Dict[str, int]:
        """Cancel all tasks in a batch"""
        
        cancelled_count = 0
        total_count = 0
        
        # Find all tasks in batch
        all_task_ids = (
            list(self.task_queue._running_tasks.keys()) +
            list(self.task_queue._completed_tasks.keys())
        )
        
        batch_task_ids = [tid for tid in all_task_ids if tid.startswith(batch_id)]
        
        for task_id in batch_task_ids:
            total_count += 1
            if await self.task_queue.cancel_task(task_id):
                cancelled_count += 1
        
        logger.info(f"🚫 Batch cancellation: {batch_id} - {cancelled_count}/{total_count} cancelled")
        
        return {
            "batch_id": batch_id,
            "total_tasks": total_count,
            "cancelled_tasks": cancelled_count,
            "already_completed": total_count - cancelled_count
        }
    
    async def shutdown(self):
        """Shutdown async interface gracefully"""
        
        logger.info("🔄 Shutting down async interface...")
        
        # Shutdown task queue
        self.task_queue.shutdown()
        
        # Cancel background processor
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        logger.info("✅ Async interface shutdown complete")
    
    def __del__(self):
        """Cleanup on garbage collection"""
        try:
            if self._processor_task and not self._processor_task.done():
                self._processor_task.cancel()
        except:
            pass

# Async context managers for resource management
class AsyncMCPSession:
    """Async context manager for MCP operations with automatic cleanup"""
    
    def __init__(self, interface: AsyncMCPInterface, session_name: str = None):
        self.interface = interface
        self.session_name = session_name or str(uuid.uuid4())
        self.task_ids = []
    
    async def __aenter__(self):
        self.interface._active_sessions.add(self)
        logger.info(f"🔗 Async session started: {self.session_name}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cancel any pending tasks in this session
        for task_id in self.task_ids:
            await self.interface.task_queue.cancel_task(task_id)
        
        try:
            self.interface._active_sessions.remove(self)
        except KeyError:
            pass
        
        logger.info(f"🔗 Async session ended: {self.session_name}")
    
    async def enqueue_task(self, operation: str, parameters: Dict[str, Any], **kwargs) -> str:
        """Enqueue a task within this session"""
        
        task = AsyncTask(
            task_id=str(uuid.uuid4()),
            operation=operation,
            parameters=parameters,
            **kwargs
        )
        
        task_id = await self.interface.task_queue.enqueue(task)
        self.task_ids.append(task_id)
        return task_id

# Convenience functions for direct API usage
async def create_async_interface(max_concurrent: int = 4, 
                               max_threads: int = 8,
                               enable_batching: bool = True) -> AsyncMCPInterface:
    """Create and initialize async MCP interface"""
    
    interface = AsyncMCPInterface(
        max_concurrent=max_concurrent,
        max_threads=max_threads,
        enable_batching=enable_batching
    )
    
    logger.info(f"🚀 Async MCP interface created: concurrent={max_concurrent}, threads={max_threads}")
    return interface

async def process_videos_concurrently(video_files: List[str],
                                    operation: str = "analyze_keyframes",
                                    max_concurrent: int = 4) -> List[TaskResult]:
    """Convenience function for concurrent video processing"""
    
    interface = await create_async_interface(max_concurrent=max_concurrent)
    
    try:
        # Start batch processing
        batch_id = await interface.process_video_batch_async(
            video_files=video_files,
            operation=operation,
            priority=TaskPriority.NORMAL
        )
        
        # Wait for completion
        batch_result = await interface.wait_for_batch(batch_id)
        
        return batch_result.results
        
    finally:
        await interface.shutdown()

async def analyze_video_with_context(video_path: str,
                                   target_operation: str = "concat",
                                   timeout: float = 60.0) -> TaskResult:
    """Convenience function for async video analysis with AI context"""
    
    interface = await create_async_interface()
    
    try:
        task_id = await interface.analyze_video_async(
            video_path=video_path,
            target_operation=target_operation,
            timeout=timeout
        )
        
        return await interface.wait_for_task(task_id)
        
    finally:
        await interface.shutdown()
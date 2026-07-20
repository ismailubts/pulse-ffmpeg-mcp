"""
Trace Logger - Half-assed but useful operation breadcrumbs for post-mortem analysis
Logs operation steps to /tmp/mcp-traces/ for debugging hangs and failures
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import threading
import uuid

class TraceLogger:
    """Simple operation tracer for debugging video processing issues"""
    
    def __init__(self, base_dir: str = "/tmp/mcp-traces"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        self._lock = threading.Lock()
        self._cleanup_old_traces()
    
    def _cleanup_old_traces(self):
        """Remove traces older than 7 days"""
        try:
            cutoff = datetime.now() - timedelta(days=7)
            for day_dir in self.base_dir.iterdir():
                if day_dir.is_dir():
                    try:
                        day_date = datetime.strptime(day_dir.name, "%Y-%m-%d")
                        if day_date < cutoff:
                            import shutil
                            shutil.rmtree(day_dir)
                    except ValueError:
                        pass  # Skip non-date directories
        except Exception:
            pass  # Cleanup is optional
    
    def _get_trace_file(self, operation_id: str) -> Path:
        """Get trace file path for operation"""
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = self.base_dir / today
        day_dir.mkdir(exist_ok=True)
        return day_dir / f"{operation_id}.jsonl"
    
    def _write_entry(self, operation_id: str, entry: Dict[str, Any]):
        """Thread-safe write of trace entry"""
        entry["ts"] = datetime.now().isoformat()
        entry["op_id"] = operation_id
        
        with self._lock:
            trace_file = self._get_trace_file(operation_id)
            with open(trace_file, "a") as f:
                json.dump(entry, f, separators=(',', ':'))
                f.write('\n')
    
    def start_operation(self, operation_type: str, params: Dict[str, Any] = None) -> str:
        """Start tracing an operation, returns operation_id"""
        timestamp = int(time.time())
        op_id = f"{operation_type}_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        self._write_entry(op_id, {
            "step": "start",
            "action": operation_type,
            "params": params or {}
        })
        return op_id
    
    def log_step(self, operation_id: str, step: str, action: str, **kwargs):
        """Log a step within an operation"""
        entry = {
            "step": step,
            "action": action,
            **kwargs
        }
        self._write_entry(operation_id, entry)
    
    def log_ffmpeg_command(self, operation_id: str, cmd: List[str], pid: Optional[int] = None):
        """Log FFmpeg command execution"""
        self._write_entry(operation_id, {
            "step": "ffmpeg_cmd",
            "action": "ffmpeg_exec",
            "cmd": cmd,
            "pid": pid,
            "cmd_str": " ".join(cmd)
        })
    
    def log_ffmpeg_result(self, operation_id: str, success: bool, duration_ms: Optional[int] = None, 
                         stdout: str = "", stderr: str = "", pid: Optional[int] = None):
        """Log FFmpeg command result"""
        self._write_entry(operation_id, {
            "step": "ffmpeg_result",
            "action": "ffmpeg_complete",
            "success": success,
            "duration_ms": duration_ms,
            "stdout": stdout[:500] if stdout else "",  # Truncate logs
            "stderr": stderr[:500] if stderr else "",
            "pid": pid
        })
    
    def log_process_spawn(self, operation_id: str, cmd: List[str], pid: int, process_type: str = "subprocess"):
        """Log process spawn"""
        self._write_entry(operation_id, {
            "step": "process_spawn",
            "action": process_type,
            "cmd": cmd,
            "pid": pid
        })
    
    def log_zombie_scan(self, operation_id: str, found_pids: List[int], action: str = "scan"):
        """Log zombie process detection"""
        self._write_entry(operation_id, {
            "step": "zombie_scan", 
            "action": action,
            "found_pids": found_pids,
            "zombie_count": len(found_pids)
        })
    
    def log_timeout(self, operation_id: str, timeout_seconds: int, operation: str):
        """Log timeout event"""
        self._write_entry(operation_id, {
            "step": "timeout",
            "action": "timeout_reached",
            "timeout_seconds": timeout_seconds,
            "operation": operation
        })
    
    def log_file_operation(self, operation_id: str, action: str, file_path: str, success: bool = True, size_bytes: Optional[int] = None):
        """Log file operations"""
        self._write_entry(operation_id, {
            "step": "file_op",
            "action": action,
            "file_path": str(file_path),
            "success": success,
            "size_bytes": size_bytes
        })
    
    def end_operation(self, operation_id: str, success: bool, error: str = None, **kwargs):
        """End operation tracing"""
        entry = {
            "step": "end",
            "action": "operation_complete",
            "success": success,
            **kwargs
        }
        if error:
            entry["error"] = error
        self._write_entry(operation_id, entry)
    
    @contextmanager
    def trace_operation(self, operation_type: str, params: Dict[str, Any] = None):
        """Context manager for operation tracing"""
        op_id = self.start_operation(operation_type, params)
        try:
            yield op_id
            self.end_operation(op_id, success=True)
        except Exception as e:
            self.end_operation(op_id, success=False, error=str(e))
            raise

# Global trace logger instance
_trace_logger = None

def get_trace_logger() -> TraceLogger:
    """Get global trace logger instance"""
    global _trace_logger
    if _trace_logger is None:
        _trace_logger = TraceLogger()
    return _trace_logger

# Convenience functions
def trace_start(operation_type: str, params: Dict[str, Any] = None) -> str:
    """Start tracing operation"""
    return get_trace_logger().start_operation(operation_type, params)

def trace_step(operation_id: str, step: str, action: str, **kwargs):
    """Log operation step"""
    get_trace_logger().log_step(operation_id, step, action, **kwargs)

def trace_ffmpeg(operation_id: str, cmd: List[str], pid: Optional[int] = None):
    """Log FFmpeg command"""
    get_trace_logger().log_ffmpeg_command(operation_id, cmd, pid)

def trace_ffmpeg_result(operation_id: str, success: bool, **kwargs):
    """Log FFmpeg result"""
    get_trace_logger().log_ffmpeg_result(operation_id, success, **kwargs)

def trace_end(operation_id: str, success: bool, **kwargs):
    """End operation tracing"""
    get_trace_logger().end_operation(operation_id, success, **kwargs)
"""
Containerized FFmpeg Wrapper - Execute FFmpeg in isolated Docker containers
Provides clean separation between main app and multimedia processing
"""

import asyncio
import json
import os
import shutil
import time
try:
    import docker
except ImportError:
    docker = None  # Optional dependency
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from contextlib import asynccontextmanager

from .trace_logger import get_trace_logger


class PathTranslator:
    """Handles translation between host paths and container paths"""
    
    def __init__(self, base_input_dir: Path, base_output_dir: Path, base_metadata_dir: Path):
        self.base_input_dir = Path(base_input_dir).resolve()
        self.base_output_dir = Path(base_output_dir).resolve()
        self.base_metadata_dir = Path(base_metadata_dir).resolve()
        
        # Container mount points
        self.container_input = "/input"
        self.container_output = "/output"
        self.container_metadata = "/metadata"
    
    def translate_path_to_container(self, host_path: str) -> str:
        """Translate host path to container path"""
        host_path = Path(host_path).resolve()
        
        # Check which base directory this path belongs to
        try:
            rel_to_input = host_path.relative_to(self.base_input_dir)
            return f"{self.container_input}/{rel_to_input}"
        except ValueError:
            pass
            
        try:
            rel_to_output = host_path.relative_to(self.base_output_dir)
            return f"{self.container_output}/{rel_to_output}"
        except ValueError:
            pass
            
        try:
            rel_to_metadata = host_path.relative_to(self.base_metadata_dir)
            return f"{self.container_metadata}/{rel_to_metadata}"
        except ValueError:
            pass
        
        # If not in any base directory, assume it's relative to output
        if not host_path.is_absolute():
            return f"{self.container_output}/{host_path}"
        
        raise ValueError(f"Path {host_path} is not within allowed directories")
    
    def translate_command(self, cmd: List[str]) -> List[str]:
        """Translate file paths in FFmpeg command"""
        translated_cmd = []
        
        for arg in cmd:
            # Skip ffmpeg binary name
            if arg == "ffmpeg":
                continue
                
            # Try to translate if it looks like a file path
            if any(x in arg for x in ['.mp4', '.mp3', '.wav', '.avi', '.mov', '.mkv', '.flv', '.m4v']):
                try:
                    translated_arg = self.translate_path_to_container(arg)
                    translated_cmd.append(translated_arg)
                    continue
                except (ValueError, OSError):
                    pass
            
            # Keep argument as-is if not a file path
            translated_cmd.append(arg)
        
        return translated_cmd
    
    def get_volume_mounts(self) -> Dict[str, Dict[str, str]]:
        """Get Docker volume mount configuration"""
        return {
            str(self.base_input_dir): {
                'bind': self.container_input,
                'mode': 'ro'  # Read-only
            },
            str(self.base_output_dir): {
                'bind': self.container_output,
                'mode': 'rw'  # Read-write
            },
            str(self.base_metadata_dir): {
                'bind': self.container_metadata,
                'mode': 'rw'  # Read-write
            }
        }


class ContainerizedFFmpeg:
    """FFmpeg execution via Docker containers"""
    
    def __init__(self, 
                 container_image: str = "pulse-ffmpeg-runner:latest",
                 base_input_dir: str = "/tmp/music/source",
                 base_output_dir: str = "/tmp/music/temp", 
                 base_metadata_dir: str = "/tmp/music/metadata"):
        
        self.container_image = container_image
        self.docker_client = None
        self.path_translator = PathTranslator(
            Path(base_input_dir),
            Path(base_output_dir), 
            Path(base_metadata_dir)
        )
        
        # Ensure directories exist
        self.path_translator.base_input_dir.mkdir(parents=True, exist_ok=True)
        self.path_translator.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.path_translator.base_metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_docker_client(self):
        """Get Docker client with lazy initialization"""
        if self.docker_client is None:
            try:
                self.docker_client = docker.from_env()
                # Test connection
                self.docker_client.ping()
            except Exception as e:
                raise RuntimeError(f"Failed to connect to Docker: {e}")
        return self.docker_client
    
    def _ensure_container_image(self):
        """Ensure FFmpeg runner image is available"""
        client = self._get_docker_client()
        
        try:
            client.images.get(self.container_image)
            return  # Image exists
        except docker.errors.ImageNotFound:
            pass
        
        # Try to build image from local Dockerfile
        dockerfile_path = Path(__file__).parent.parent / "docker" / "ffmpeg-runner"
        if dockerfile_path.exists():
            try:
                image, logs = client.images.build(
                    path=str(dockerfile_path.parent),
                    dockerfile=str(dockerfile_path / "Dockerfile"),
                    tag=self.container_image,
                    rm=True
                )
                print(f"✅ Built FFmpeg container: {self.container_image}")
                return
            except Exception as e:
                raise RuntimeError(f"Failed to build FFmpeg container: {e}")
        
        # Try to pull from registry as fallback
        try:
            client.images.pull(self.container_image)
        except Exception as e:
            raise RuntimeError(f"FFmpeg container image not found: {self.container_image}. Error: {e}")
    
    async def execute_command(self, command: List[str], timeout: int = 300) -> Dict[str, Any]:
        """Execute FFmpeg command in container"""
        from .trace_logger import get_trace_logger
        
        # Get operation ID from context or create one
        op_id = getattr(asyncio.current_task(), 'trace_operation_id', None)
        if not op_id:
            op_id = get_trace_logger().start_operation("containerized_ffmpeg", {"command": command})
        
        try:
            # Ensure container image is available
            self._ensure_container_image()
            
            # Translate command paths (remove ffmpeg binary since container entrypoint handles it)
            container_command = self.path_translator.translate_command(command)
            
            # Log the containerized command
            get_trace_logger().log_step(
                op_id, "container_prep", "path_translation",
                original_command=command,
                container_command=container_command,
                volumes=self.path_translator.get_volume_mounts()
            )
            
            # Execute in container
            start_time = time.time()
            result = await self._run_container(container_command, timeout, op_id)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log result
            get_trace_logger().log_ffmpeg_result(
                op_id, result["success"], duration_ms, 
                result.get("stdout", ""), result.get("stderr", "")
            )
            
            return result
            
        except Exception as e:
            get_trace_logger().log_step(
                op_id, "container_error", "execution_failed",
                error=str(e), command=command
            )
            return {
                "success": False,
                "error": f"Container execution failed: {str(e)}",
                "command": ' '.join(command)
            }
    
    async def _run_container(self, command: List[str], timeout: int, op_id: str) -> Dict[str, Any]:
        """Run Docker container with FFmpeg command"""
        client = self._get_docker_client()
        
        container_config = {
            'image': self.container_image,
            'command': command,
            'volumes': self.path_translator.get_volume_mounts(),
            'working_dir': '/workspace',
            'user': 'ffmpeg',
            'remove': False,  # Keep container for debugging initially
            'network_mode': 'none',  # No network access for security
            'mem_limit': '2g',  # 2GB memory limit
            'cpu_count': 2,  # 2 CPU cores max
            'detach': True
        }
        
        try:
            # Create and start container
            container = client.containers.run(**container_config)
            
            get_trace_logger().log_process_spawn(
                op_id, command, container.id, "docker_container"
            )
            
            # Wait for completion with timeout
            try:
                # Simple wait with timeout
                result = container.wait(timeout=timeout)
                logs = container.logs()
                
                success = result['StatusCode'] == 0
                stdout = logs.decode('utf-8', errors='ignore') if logs else ""
                stderr = ""
                
                # For FFmpeg, stdout/stderr are often combined
                if not success and stdout:
                    stderr = stdout
                    stdout = ""
                
                return {
                    "success": success,
                    "returncode": result['StatusCode'],
                    "stdout": stdout,
                    "stderr": stderr,
                    "command": ' '.join(command),
                    "container_id": container.id[:12]
                }
                
            except docker.errors.ContainerError as e:
                return {
                    "success": False,
                    "returncode": e.exit_status,
                    "stdout": "",
                    "stderr": str(e),
                    "command": ' '.join(command),
                    "container_id": container.id[:12]
                }
            
        except Exception as e:
            get_trace_logger().log_timeout(op_id, timeout, "container_execution")
            return {
                "success": False,
                "error": f"Container execution error: {str(e)}",
                "command": ' '.join(command)
            }
    
    def is_available(self) -> bool:
        """Check if containerized FFmpeg is available"""
        try:
            self._ensure_container_image()
            return True
        except Exception:
            return False
    
    @asynccontextmanager
    async def temp_workspace(self):
        """Create temporary workspace for container operations"""
        workspace_id = f"ffmpeg_workspace_{int(time.time())}"
        temp_input = self.path_translator.base_input_dir / workspace_id
        temp_output = self.path_translator.base_output_dir / workspace_id
        
        try:
            temp_input.mkdir(exist_ok=True)
            temp_output.mkdir(exist_ok=True)
            
            # Create temporary path translator for this workspace
            temp_translator = PathTranslator(temp_input, temp_output, self.path_translator.base_metadata_dir)
            
            yield {
                'input_dir': temp_input,
                'output_dir': temp_output,
                'translator': temp_translator
            }
            
        finally:
            # Cleanup temporary directories
            if temp_input.exists():
                shutil.rmtree(temp_input, ignore_errors=True)
            if temp_output.exists():
                shutil.rmtree(temp_output, ignore_errors=True)


# Compatibility functions for drop-in replacement
async def execute_containerized_ffmpeg(command: List[str], timeout: int = 300) -> Dict[str, Any]:
    """Execute FFmpeg command in container - drop-in replacement function"""
    ffmpeg = ContainerizedFFmpeg()
    return await ffmpeg.execute_command(command, timeout)


def is_containerized_ffmpeg_available() -> bool:
    """Check if containerized FFmpeg is available"""
    try:
        ffmpeg = ContainerizedFFmpeg()
        return ffmpeg.is_available()
    except Exception:
        return False
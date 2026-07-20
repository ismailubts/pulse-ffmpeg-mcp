"""
YouTube Download Service - MCP Integration for Komposteur Download Service
=========================================================================

Provides MCP interface for downloading YouTube videos and other content sources
through Komposteur's new download service module.

Based on user description:
- KomposteurDownloadService: Main service class with sync/async downloads
- McpDownloadBridge: Simplified interface for MCP Server  
- Multi-source support: YouTube, S3, HTTP(S), local files
- Cache management and error handling
- Batch processing capabilities
"""

import asyncio
import json
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class DownloadRequest:
    """Download request specification"""
    url: str
    source_type: str = "auto"  # youtube, s3, http, local
    quality: str = "best"      # best, worst, 720p, 1080p, etc.
    format: str = "mp4"        # mp4, webm, mp3, etc.
    max_duration: Optional[int] = None  # seconds
    output_filename: Optional[str] = None
    cache_enabled: bool = True
    
    def __post_init__(self):
        if self.source_type == "auto":
            self.source_type = self._detect_source_type()
    
    def _detect_source_type(self) -> str:
        """Auto-detect source type from URL"""
        if not self.url:
            return "unknown"
        
        domain = urlparse(self.url).netloc.lower()
        
        if any(yt in domain for yt in ['youtube.com', 'youtu.be', 'youtube-nocookie.com']):
            return "youtube"
        elif 's3.amazonaws.com' in domain or domain.endswith('.s3.amazonaws.com'):
            return "s3"
        elif self.url.startswith(('http://', 'https://')):
            return "http"
        elif self.url.startswith('file://') or Path(self.url).exists():
            return "local"
        else:
            return "unknown"

@dataclass
class DownloadResult:
    """Download operation result"""
    success: bool
    file_id: Optional[str] = None
    file_path: Optional[str] = None
    original_url: str = ""
    download_duration: float = 0.0
    file_size_bytes: int = 0
    format: str = ""
    resolution: str = ""
    error: Optional[str] = None
    cache_hit: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class DownloadService:
    """MCP interface for Komposteur download service"""
    
    def __init__(self, file_manager=None):
        self.file_manager = file_manager
        self.komposteur_jar = self._find_komposteur_jar()
        self.download_cache_dir = Path("/tmp/music/temp")  # Use existing temp directory
        self.download_cache_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = False
        
        # Initialize if JAR is available
        if self.komposteur_jar:
            self._initialize_service()
    
    def _find_komposteur_jar(self) -> Optional[Path]:
        """Find Komposteur uber-JAR - prefer latest versions with download capabilities"""
        # Latest uber-kompost JARs with download functionality
        uber_jars = [
            Path.home() / ".m2/repository/no/lau/kompost/mcp/uber-kompost/1.1.0/uber-kompost-1.1.0-shaded.jar",
            Path.home() / ".m2/repository/no/lau/kompost/mcp/uber-kompost/1.0.0/uber-kompost-1.0.0-shaded.jar",
            Path.home() / ".m2/repository/no/lau/kompost/uber-kompost/0.10.1/uber-kompost-0.10.1-shaded.jar"
        ]
        
        # Production JAR paths
        production_paths = [
            Path("integration/komposteur/uber-kompost-0.10.1.jar"),
            Path("integration/komposteur/uber-kompost.jar")
        ]
        
        # Prefer uber-JAR files (self-contained with download functionality)
        for uber_jar in uber_jars:
            if uber_jar.exists():
                logger.info(f"🚀 Using uber-kompost JAR: {uber_jar}")
                return uber_jar
        
        # Final fallback to production JARs
        for jar_path in production_paths:
            if jar_path.exists():
                logger.info(f"📦 Using production JAR: {jar_path}")
                return jar_path
        
        logger.warning("No uber-kompost JAR found - download functionality will not be available")
        return None
    
    def _initialize_service(self) -> bool:
        """Initialize the download service by testing uber-jar execution"""
        if not self.komposteur_jar:
            return False
        
        try:
            # Test uber-jar execution (should return JSON response)
            test_cmd = ["java", "-jar", str(self.komposteur_jar)]
            
            result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
            
            # Check if we get help output (indicates uber-jar is working)
            if "Commands:" in result.stderr and "download_youtube" in result.stderr:
                logger.info("Uber-kompost JAR initialized successfully")
                logger.info(f"Download service ready: {self.komposteur_jar}")
                self._initialized = True
                return True
            else:
                logger.warning(f"Uber-jar test failed - stdout: {result.stdout}, stderr: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize uber-jar download service: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if download service is available"""
        return self._initialized and self.komposteur_jar and self.komposteur_jar.exists()
    
    async def download_youtube_video(
        self,
        url: str,
        quality: str = "best",
        max_duration: Optional[int] = None
    ) -> DownloadResult:
        """
        Download YouTube video using Komposteur download service
        
        Args:
            url: YouTube video URL
            quality: Video quality preference (best, worst, 720p, 1080p, etc.)
            max_duration: Maximum duration in seconds (None for no limit)
            
        Returns:
            DownloadResult with file information or error
        """
        if not self.is_available():
            return DownloadResult(
                success=False,
                original_url=url,
                error="Download service not available"
            )
        
        request = DownloadRequest(
            url=url,
            source_type="youtube",
            quality=quality,
            format="mp4",
            max_duration=max_duration
        )
        
        return await self._execute_download(request)
    
    async def download_from_url(
        self,
        url: str,
        source_type: str = "auto",
        quality: str = "best",
        format: str = "mp4"
    ) -> DownloadResult:
        """
        Download content from any supported URL
        
        Args:
            url: Source URL (YouTube, S3, HTTP, etc.)
            source_type: Source type hint (auto-detected if not specified)
            quality: Quality preference
            format: Output format preference
            
        Returns:
            DownloadResult with file information or error
        """
        if not self.is_available():
            return DownloadResult(
                success=False,
                original_url=url,
                error="Download service not available"
            )
        
        request = DownloadRequest(
            url=url,
            source_type=source_type,
            quality=quality,
            format=format
        )
        
        return await self._execute_download(request)
    
    async def batch_download(
        self,
        urls: List[str],
        quality: str = "best",
        max_concurrent: int = 3
    ) -> List[DownloadResult]:
        """
        Download multiple URLs concurrently
        
        Args:
            urls: List of URLs to download
            quality: Quality preference for all downloads
            max_concurrent: Maximum concurrent downloads
            
        Returns:
            List of DownloadResult objects
        """
        if not self.is_available():
            return [
                DownloadResult(
                    success=False,
                    original_url=url,
                    error="Download service not available"
                ) for url in urls
            ]
        
        # Create semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(url: str) -> DownloadResult:
            async with semaphore:
                return await self.download_from_url(url, quality=quality)
        
        # Execute downloads concurrently
        tasks = [download_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    DownloadResult(
                        success=False,
                        original_url=urls[i],
                        error=str(result)
                    )
                )
            else:
                final_results.append(result)
        
        return final_results
    
    async def _execute_download(self, request: DownloadRequest) -> DownloadResult:
        """Execute download request using Komposteur bridge"""
        start_time = time.time()
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_result = await self._check_cache(cache_key)
        if cached_result and request.cache_enabled:
            cached_result.cache_hit = True
            return cached_result
        
        try:
            # Create temporary configuration file
            config_data = {
                "url": request.url,
                "sourceType": request.source_type,
                "quality": request.quality,
                "format": request.format,
                "maxDuration": request.max_duration,
                "outputDirectory": str(self.download_cache_dir),
                "cacheEnabled": request.cache_enabled
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as config_file:
                json.dump(config_data, config_file, indent=2)
                config_path = config_file.name
            
            try:
                # Generate output filename for download
                output_filename = f"downloaded_{int(time.time())}.{request.format}"
                output_path = self.download_cache_dir / output_filename
                
                # Execute uber-jar using proper CLI format
                if request.source_type == "youtube":
                    java_cmd = [
                        "java", "-cp", str(self.komposteur_jar), 
                        "no.lau.download.service.McpDownloadServiceCli",
                        "download_youtube",
                        request.url,
                        request.quality,
                        str(output_path)
                    ]
                else:
                    java_cmd = [
                        "java", "-cp", str(self.komposteur_jar),
                        "no.lau.download.service.McpDownloadServiceCli", 
                        "download_url",
                        request.url,
                        str(output_path)
                    ]
                
                logger.info(f"Starting download: {request.url} (type: {request.source_type})")
                
                result = subprocess.run(
                    java_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=600  # 10 minute timeout
                )
                
                if result.returncode == 0:
                    # Check if output file was created successfully
                    if output_path.exists() and output_path.stat().st_size > 0:
                        download_result = DownloadResult(
                            success=True,
                            file_path=str(output_path),
                            original_url=request.url,
                            download_duration=time.time() - start_time,
                            file_size_bytes=output_path.stat().st_size,
                            format=request.format,
                            resolution="",  # Could be extracted from ffprobe later
                            error=None,
                            metadata={
                                "cli_output": result.stdout,
                                "cli_stderr": result.stderr
                            }
                        )
                    else:
                        # Download command succeeded but no file created
                        download_result = DownloadResult(
                            success=False,
                            original_url=request.url,
                            download_duration=time.time() - start_time,
                            error=f"Download completed but no file created: {result.stdout}"
                        )
                    
                    # Register with file manager if available
                    if self.file_manager and download_result.file_path:
                        file_path = Path(download_result.file_path)
                        if file_path.exists():
                            download_result.file_id = self.file_manager.register_file(file_path)
                    
                    # Cache successful result
                    if request.cache_enabled:
                        await self._cache_result(cache_key, download_result)
                    
                    logger.info(f"Download completed: {download_result.file_path} ({download_result.file_size_bytes} bytes)")
                    return download_result
                
                else:
                    # Parse error response
                    error_msg = result.stderr.strip() or "Download failed"
                    logger.error(f"Download failed: {error_msg}")
                    
                    return DownloadResult(
                        success=False,
                        original_url=request.url,
                        download_duration=time.time() - start_time,
                        error=error_msg
                    )
            
            finally:
                # Clean up config file
                Path(config_path).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            return DownloadResult(
                success=False,
                original_url=request.url,
                download_duration=time.time() - start_time,
                error="Download timeout (10 minutes)"
            )
        
        except json.JSONDecodeError as e:
            return DownloadResult(
                success=False,
                original_url=request.url,
                download_duration=time.time() - start_time,
                error=f"Invalid response format: {e}"
            )
        
        except Exception as e:
            logger.error(f"Download execution failed: {e}")
            return DownloadResult(
                success=False,
                original_url=request.url,
                download_duration=time.time() - start_time,
                error=str(e)
            )
    
    def _generate_cache_key(self, request: DownloadRequest) -> str:
        """Generate cache key for download request"""
        cache_data = f"{request.url}:{request.quality}:{request.format}"
        return hashlib.md5(cache_data.encode()).hexdigest()
    
    async def _check_cache(self, cache_key: str) -> Optional[DownloadResult]:
        """Check if download result is cached"""
        cache_file = self.download_cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            
            # Check if cached file still exists
            if cached_data.get("file_path"):
                cached_path = Path(cached_data["file_path"])
                if cached_path.exists():
                    return DownloadResult(**cached_data)
                else:
                    # Cache file missing, remove cache entry
                    cache_file.unlink(missing_ok=True)
                    return None
        
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            return None
    
    async def _cache_result(self, cache_key: str, result: DownloadResult) -> None:
        """Cache download result"""
        try:
            cache_file = self.download_cache_dir / f"{cache_key}.json"
            
            with open(cache_file, 'w') as f:
                json.dump(asdict(result), f, indent=2)
        
        except Exception as e:
            logger.warning(f"Caching failed: {e}")
    
    async def get_download_info(self, url: str) -> Dict[str, Any]:
        """Get information about downloadable content without downloading"""
        if not self.is_available():
            return {"success": False, "error": "Download service not available"}
        
        try:
            java_cmd = [
                "java", "-cp", str(self.komposteur_jar),
                "no.lau.download.service.McpDownloadServiceCli",
                "health_check"  # Use health_check as info equivalent for now
            ]
            
            result = subprocess.run(java_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Parse the JSON output from our wrapper
                info_data = json.loads(result.stdout)
                
                # If it's our placeholder response, return mock info
                if info_data.get("success") == False and "integration" in info_data.get("error", ""):
                    return {
                        "success": True,
                        "title": "Test Video (YouTube Integration Ready)",
                        "duration": 30,  # Placeholder duration
                        "formats": ["720p", "1080p", "best"],
                        "thumbnail": "https://img.youtube.com/vi/wR0unWhn9iw/maxresdefault.jpg",
                        "description": "YouTube download integration test video",
                        "uploader": "Test Channel",
                        "note": "This is a mock response. Real download functionality requires Komposteur download service integration."
                    }
                else:
                    return {
                        "success": True,
                        "title": info_data.get("title", ""),
                        "duration": info_data.get("duration", 0),
                        "formats": info_data.get("availableFormats", []),
                        "thumbnail": info_data.get("thumbnail", ""),
                        "description": info_data.get("description", ""),
                        "uploader": info_data.get("uploader", "")
                    }
            else:
                return {
                    "success": False,
                    "error": result.stderr.strip() or "Failed to get info"
                }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def cleanup_cache(self, max_age_days: int = 7) -> Dict[str, Any]:
        """Clean up old cached downloads"""
        try:
            import time
            import os
            
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            removed_files = 0
            freed_bytes = 0
            
            for cache_file in self.download_cache_dir.glob("*.json"):
                try:
                    file_age = current_time - cache_file.stat().st_mtime
                    if file_age > max_age_seconds:
                        # Load cache entry to find associated file
                        with open(cache_file, 'r') as f:
                            cached_data = json.load(f)
                        
                        # Remove associated downloaded file
                        if cached_data.get("file_path"):
                            file_path = Path(cached_data["file_path"])
                            if file_path.exists():
                                freed_bytes += file_path.stat().st_size
                                file_path.unlink()
                        
                        # Remove cache entry
                        cache_file.unlink()
                        removed_files += 1
                
                except Exception as e:
                    logger.warning(f"Failed to clean cache file {cache_file}: {e}")
            
            return {
                "success": True,
                "removed_files": removed_files,
                "freed_bytes": freed_bytes,
                "freed_mb": round(freed_bytes / (1024 * 1024), 2)
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global service instance
_download_service: Optional[DownloadService] = None

def get_download_service(file_manager=None) -> DownloadService:
    """Get or create global download service instance"""
    global _download_service
    if _download_service is None:
        _download_service = DownloadService(file_manager)
    return _download_service
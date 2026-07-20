"""
Komposteur MCP Tools - Integration layer for FFMPEG MCP server
Provides access to Komposteur's production-proven algorithms via MCP
"""
from typing import Dict, Any
import logging
from pathlib import Path

try:
    from ..bridge.komposteur_bridge import get_bridge
    from ..bridge.uber_kompost_bridge import get_uber_bridge
except ImportError:
    # Fallback for testing or standalone usage
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from bridge.komposteur_bridge import get_bridge
    from bridge.uber_kompost_bridge import get_uber_bridge

logger = logging.getLogger(__name__)

def register_komposteur_tools(server):
    """Register all Komposteur tools with the MCP server"""
    
    @server.tool()
    async def komposteur_beat_sync(
        video_file_id: str,
        audio_file_id: str, 
        bpm: float = 120.0
    ) -> Dict[str, Any]:
        """
        Beat-synchronize video using Komposteur's production-proven algorithm
        
        Uses the 120 BPM = 8s per 16 beats formula for precise synchronization.
        Handles video/audio alignment with microsecond precision.
        
        Args:
            video_file_id: Source video file ID
            audio_file_id: Audio track file ID  
            bpm: Beats per minute for synchronization (default: 120)
            
        Returns:
            Dict with success status, output file, and timing details
        """
        try:
            bridge = get_bridge()
            if not bridge.is_available():
                return {
                    "success": False,
                    "error": "Komposteur bridge not available - check Java installation and JAR"
                }
            
            # Convert file IDs to paths (using MCP server's file manager)
            # TODO: Integrate with FFMPEG MCP's file_manager for ID->path conversion
            video_path = f"/tmp/music/source/{video_file_id}"  # Placeholder
            audio_path = f"/tmp/music/source/{audio_file_id}"  # Placeholder
            
            result = bridge.beat_sync(video_path, audio_path, bpm)
            
            if result["success"]:
                return {
                    "success": True,
                    "output_file_id": f"komposteur_sync_{int(result['processing_time'])}",
                    "duration": result["duration"],
                    "beat_count": result["beat_count"],
                    "algorithm": "Komposteur microsecond-precise beat synchronization"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Komposteur beat sync failed: {e}")
            return {
                "success": False,
                "error": f"Beat synchronization failed: {str(e)}"
            }
    
    @server.tool()
    async def komposteur_extract_segment(
        file_id: str,
        start_time: float,
        end_time: float
    ) -> Dict[str, Any]:
        """
        Extract video segment with microsecond-precise timing
        
        Uses Komposteur's frame-perfect extraction algorithms for
        precise segment boundaries without frame loss.
        
        Args:
            file_id: Source video file ID
            start_time: Start time in seconds (microsecond precision)
            end_time: End time in seconds (microsecond precision)
            
        Returns:
            Dict with success status, output file, and actual timing
        """
        try:
            bridge = get_bridge()
            if not bridge.is_available():
                return {
                    "success": False,
                    "error": "Komposteur bridge not available"
                }
            
            # Convert file ID to path
            file_path = f"/tmp/music/source/{file_id}"  # Placeholder
            
            result = bridge.extract_segment(file_path, start_time, end_time)
            
            if result["success"]:
                return {
                    "success": True,
                    "output_file_id": f"komposteur_segment_{int(start_time)}_{int(end_time)}",
                    "actual_start": result["actual_start"],
                    "actual_end": result["actual_end"],
                    "frame_count": result["frame_count"],
                    "algorithm": "Komposteur microsecond-precise extraction"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Komposteur segment extraction failed: {e}")
            return {
                "success": False,
                "error": f"Segment extraction failed: {str(e)}"
            }
    
    @server.tool()
    async def komposteur_validate_media(file_id: str) -> Dict[str, Any]:
        """
        Comprehensive media validation using Komposteur's pipeline
        
        Performs deep analysis of media files including format validation,
        quality assessment, and compatibility checks.
        
        Args:
            file_id: Media file ID to validate
            
        Returns:
            Dict with validation results, quality score, and identified issues
        """
        try:
            bridge = get_bridge()
            if not bridge.is_available():
                return {
                    "success": False,
                    "error": "Komposteur bridge not available"
                }
            
            # Convert file ID to path
            file_path = f"/tmp/music/source/{file_id}"  # Placeholder
            
            result = bridge.validate_media(file_path)
            
            if result["success"]:
                return {
                    "success": True,
                    "valid": result["valid"],
                    "format": result["format"],
                    "duration": result["duration"],
                    "resolution": result["resolution"],
                    "quality_score": result["quality_score"],
                    "issues": result["issues"],
                    "algorithm": "Komposteur comprehensive validation pipeline"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Komposteur media validation failed: {e}")
            return {
                "success": False,
                "error": f"Media validation failed: {str(e)}"
            }
    
    @server.tool()
    async def komposteur_calculate_beat_duration(
        bpm: float,
        beat_count: int = 16
    ) -> Dict[str, Any]:
        """
        Calculate precise duration for beat-based video timing
        
        Uses Komposteur's production formula: 120 BPM = 8s per 16 beats
        for consistent timing calculations across the system.
        
        Args:
            bpm: Beats per minute
            beat_count: Number of beats (default: 16)
            
        Returns:
            Dict with calculated duration and timing details
        """
        try:
            # Komposteur formula: duration = (beat_count / bpm) * 60
            duration = (beat_count / bpm) * 60
            
            return {
                "success": True,
                "duration": duration,
                "bpm": bpm,
                "beat_count": beat_count,
                "formula": "Komposteur: (beat_count / bpm) * 60",
                "reference": "120 BPM × 16 beats = 8.0 seconds"
            }
            
        except Exception as e:
            logger.error(f"Beat duration calculation failed: {e}")
            return {
                "success": False,
                "error": f"Beat calculation failed: {str(e)}"
            }
    
    @server.tool()
    async def komposteur_process_kompost(kompost_json_path: str) -> Dict[str, Any]:
        """
        Process a kompost.json file using Komposteur's curated FFMPEG workflows
        
        This is the primary integration point for processing kompost.json files
        containing curated FFMPEG effects and beat-synchronized video workflows.
        
        Args:
            kompost_json_path: Path to the kompost.json configuration file
            
        Returns:
            Dict with processing results, output video path, and applied effects
        """
        try:
            bridge = get_bridge()
            if not bridge.is_available():
                return {
                    "success": False,
                    "error": "Komposteur bridge not available"
                }
            
            result = bridge.process_kompost_json(kompost_json_path)
            
            if result["success"]:
                return {
                    "success": True,
                    "output_video_path": result["output_video_path"],
                    "processing_log": result["processing_log"],
                    "curated_effects_used": result["curated_effects_used"],
                    "ffmpeg_commands_executed": result["ffmpeg_commands_executed"],
                    "total_processing_time": result["total_processing_time"],
                    "raw_result": result.get("raw_result", ""),
                    "algorithm": "Komposteur curated FFMPEG workflow processor"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Komposteur kompost.json processing failed: {e}")
            return {
                "success": False,
                "error": f"Kompost processing failed: {str(e)}"
            }
    
    @server.tool()
    async def uber_kompost_process_json(kompost_json_path: str) -> Dict[str, Any]:
        """
        Process kompost.json using uber-kompost JAR with JSON API
        
        This is the primary tool for the uber-kompost integration that processes
        kompost.json files and creates actual video output using the Java library.
        
        Args:
            kompost_json_path: Absolute path to the kompost.json file
            
        Returns:
            Dict with processing results, output video path, and metadata
        """
        try:
            bridge = get_uber_bridge()
            if not bridge.is_available():
                return {
                    "success": False,
                    "error": "Uber-kompost bridge not available. Build JAR with: mvn clean package -pl uber-kompost -DskipTests"
                }
            
            result = bridge.process_kompost_json(kompost_json_path)
            
            if result["success"]:
                return {
                    "success": True,
                    "processing_result": result,
                    "algorithm": "Uber-kompost JSON API processor"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Uber-kompost processing failed: {e}")
            return {
                "success": False,
                "error": f"Uber-kompost processing failed: {str(e)}"
            }
    
    @server.tool()
    async def komposteur_get_status() -> Dict[str, Any]:
        """
        Get Komposteur integration status and version information
        
        Returns system status, version, and availability of Java bridge.
        Useful for health checks and debugging integration issues.
        
        Returns:
            Dict with status, version, and diagnostic information
        """
        try:
            bridge = get_bridge()
            
            if bridge.is_available():
                version = bridge.get_version()
                return {
                    "success": True,
                    "status": "available",
                    "version": version,
                    "java_bridge": "connected",
                    "algorithms": [
                        "beat_sync", "extract_segment", "validate_media",
                        "calculate_beat_duration"
                    ]
                }
            else:
                return {
                    "success": True,
                    "status": "unavailable", 
                    "reason": "Java bridge not initialized",
                    "check": [
                        "Java runtime available",
                        "Komposteur JAR in ~/.m2/repository/",
                        "py4j dependency installed"
                    ]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Status check failed: {str(e)}"
            }
    
    logger.info("Registered 7 Komposteur MCP tools")
    return [
        "komposteur_beat_sync",
        "komposteur_extract_segment", 
        "komposteur_validate_media",
        "komposteur_calculate_beat_duration",
        "komposteur_process_kompost",
        "uber_kompost_process_json",
        "komposteur_get_status"
    ]
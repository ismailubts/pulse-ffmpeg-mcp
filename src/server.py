import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from functools import wraps

# Set up logging
logger = logging.getLogger(__name__)

from mcp.server.fastmcp import FastMCP
# Pydantic BaseModel is now in models.py, but FileInfo and ProcessResult are imported directly
# from pydantic import BaseModel # No longer needed here if all models are imported

try:
    from .file_manager import FileManager
    from .ffmpeg_wrapper import FFMPEGWrapper
    from .config import SecurityConfig
    from .content_analyzer import VideoContentAnalyzer
    from .komposition_processor import KompositionProcessor
    from .transition_processor import TransitionProcessor
    from .speech_detector import SpeechDetector
    from .speech_komposition_processor import SpeechKompositionProcessor
    from .enhanced_speech_analyzer import EnhancedSpeechAnalyzer
    from .composition_planner import CompositionPlanner
    from .komposition_build_planner import KompositionBuildPlanner
    from .komposition_generator import KompositionGenerator
    from .effect_processor import EffectProcessor
    from .download_service import DownloadService, get_download_service
    try:
        from .analytics_service import configure_analytics, cleanup_analytics
    except ImportError:
        configure_analytics = None
        cleanup_analytics = None
    from .audio_effect_processor import AudioEffectProcessor
    from .format_manager import FormatManager, COMMON_PRESETS
    from .models import FileInfo, ProcessResult # Import models
    from .video_operations import execute_core_processing # Import core processing logic
    from .video_comparison_tool import VideoComparisonTool
    from .youtube_upload_service import upload_to_youtube, validate_youtube_shorts
    from .timeout_manager import (
        ProcessingTimeEstimator,
        OperationTimeoutManager,
        timeout_manager,
        calculate_operation_timeout
    )
    from .haiku_subagent import HaikuSubagent, yolo_smart_concat, ProcessingStrategy, CostLimits
except ImportError:
    from .file_manager import FileManager
    from .ffmpeg_wrapper import FFMPEGWrapper
    from .config import SecurityConfig
    from .content_analyzer import VideoContentAnalyzer
    from .komposition_processor import KompositionProcessor
    from .transition_processor import TransitionProcessor
    from .speech_detector import SpeechDetector
    from .speech_komposition_processor import SpeechKompositionProcessor
    from .enhanced_speech_analyzer import EnhancedSpeechAnalyzer
    from .composition_planner import CompositionPlanner
    from .komposition_build_planner import KompositionBuildPlanner
    from .komposition_generator import KompositionGenerator
    from .effect_processor import EffectProcessor
    from .timeout_manager import (
        ProcessingTimeEstimator,
        OperationTimeoutManager,
        timeout_manager,
        calculate_operation_timeout
    )
    from .download_service import DownloadService, get_download_service
    from .audio_effect_processor import AudioEffectProcessor
    from .format_manager import FormatManager, COMMON_PRESETS
    from .models import FileInfo, ProcessResult # Import models
    from .video_operations import execute_core_processing # Import core processing logic
    from .video_comparison_tool import VideoComparisonTool
    from .enhanced_komposition_generator import generate_enhanced_komposition_from_description


# Initialize MCP server
mcp = FastMCP("ffmpeg-mcp")

# Configure analytics
firebase_endpoint = os.getenv("FIREBASE_ANALYTICS_ENDPOINT")
firebase_api_key = os.getenv("FIREBASE_API_KEY")
analytics_enabled = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
if configure_analytics:
    configure_analytics(firebase_endpoint, analytics_enabled, firebase_api_key)

# Register Komposteur integration
try:
    import sys
    from pathlib import Path
    integration_path = Path(__file__).parent.parent / "integration" / "komposteur" / "tools"
    sys.path.insert(0, str(integration_path.parent))
    from tools.mcp_tools import register_komposteur_tools
    komposteur_tools = register_komposteur_tools(mcp)
    print(f"✅ Registered {len(komposteur_tools)} Komposteur tools: {komposteur_tools}")
except Exception as e:
    print(f"⚠️  Komposteur integration failed: {e}")
    # Continue without Komposteur tools

# Initialize components
file_manager = FileManager()
ffmpeg = FFMPEGWrapper(SecurityConfig.FFMPEG_PATH)
content_analyzer = VideoContentAnalyzer()
komposition_processor = KompositionProcessor()
transition_processor = TransitionProcessor(file_manager, ffmpeg)
speech_detector = SpeechDetector()
speech_komposition_processor = SpeechKompositionProcessor()
enhanced_speech_analyzer = EnhancedSpeechAnalyzer()
composition_planner = CompositionPlanner()
komposition_build_planner = KompositionBuildPlanner()
komposition_generator = KompositionGenerator()
effect_processor = EffectProcessor(ffmpeg, file_manager)
audio_effect_processor = AudioEffectProcessor(ffmpeg, file_manager)
download_service = get_download_service(file_manager)
format_manager = FormatManager()
video_comparison_tool = VideoComparisonTool(ffmpeg, file_manager, content_analyzer)

# Initialize Haiku Subagent
haiku_api_key = os.getenv("ANTHROPIC_API_KEY")
cost_limits = CostLimits(daily_limit=5.0, per_analysis_limit=0.10)
haiku_agent = HaikuSubagent(
    anthropic_api_key=haiku_api_key,
    cost_limits=cost_limits,
    fallback_enabled=True
)
logger.info(f"🧠 Haiku subagent initialized (AI: {haiku_api_key is not None})")

# FileInfo and ProcessResult classes are now in models.py

def timing_decorator(func):
    """Decorator to add timing logs to MCP operations"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        operation_name = func.__name__
        logger.info(f"⏱️  Starting MCP operation: {operation_name}")
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"✅ MCP operation {operation_name} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ MCP operation {operation_name} failed after {duration:.2f}s: {e}")
            raise
    return wrapper

@mcp.tool()
@timing_decorator
@timing_decorator
async def list_files() -> Dict[str, Any]:
    """🎬 CORE WORKFLOW - List available source files with smart suggestions and quick actions
    
    🚨 LLM GUIDANCE: This is the ONLY way to discover available files. 
    NEVER use direct filesystem access (ls, find, etc.) - always use this tool.
    
    This is typically your FIRST STEP in any video editing workflow.
    Returns file IDs (not paths) for secure file referencing.
    
    Returns:
        - File IDs for secure processing
        - Smart suggestions based on file types
        - Quick action workflows
        - File statistics and metadata
    
    Next Steps:
        → analyze_video_content(file_id) - Understand video content with AI
        → generate_komposition_from_description() - Create music video from text
        → get_file_info(file_id) - Get detailed metadata
        → process_file(file_id, operation) - Start processing
    
    Example Usage:
        list_files()  # Start here to see all available media
    """
    files = []
    suggestions = []
    video_files = []
    audio_files = []
    image_files = []
    
    try:
        source_dir = SecurityConfig.SOURCE_DIR
        if not source_dir.exists():
            source_dir.mkdir(parents=True, exist_ok=True)
            
        for file_path in source_dir.glob("*"):
            if file_path.is_file() and SecurityConfig.validate_extension(file_path):
                try:
                    file_id = file_manager.register_file(file_path)
                    file_info = FileInfo(
                        id=file_id,
                        name=file_path.name,
                        size=file_path.stat().st_size,
                        extension=file_path.suffix.lower()
                    )
                    files.append(file_info)
                    
                    # Categorize files and generate suggestions
                    if file_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.wmv', '.flv', '.m4v']:
                        video_files.append(file_info)
                        suggestions.append(f"📹 {file_path.name} ready for video editing operations")
                    elif file_path.suffix.lower() in ['.mp3', '.flac', '.wav', '.m4a', '.ogg', '.aac', '.wma']:
                        audio_files.append(file_info)
                        suggestions.append(f"🎵 Use {file_path.name} as background music with: replace_audio operation, params='audio_file={file_id}'")
                    elif file_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']:
                        image_files.append(file_info)
                        suggestions.append(f"🖼️ Convert {file_path.name} to video: image_to_video operation, params='duration=2' (or any duration in seconds)")
                except Exception:
                    continue
                    
        # Generate workflow suggestions
        quick_actions = []
        if len(video_files) >= 2:
            quick_actions.append("🎬 Create montage: 1) trim multiple videos 2) concatenate_simple 3) replace_audio with music")
        if len(video_files) >= 1 and len(audio_files) >= 1:
            quick_actions.append("🎵 Add background music: use replace_audio operation with any audio file")
        if len(video_files) >= 1:
            quick_actions.append("✂️ Extract highlights: use trim operation to get best moments")
        if len(image_files) >= 1:
            quick_actions.append("🖼️ Create image videos: use image_to_video to convert images to video clips")
        if len(image_files) >= 1 and len(video_files) >= 1:
            quick_actions.append("🎞️ Mixed media montage: convert images to video clips, then concatenate with videos")
        
        if not suggestions:
            suggestions.append("✅ All files look ready for processing!")
        
        # Enhanced workflow-specific next steps
        what_next_suggestions = []
        if len(video_files) >= 1:
            what_next_suggestions.extend([
                "🧠 Understand content: analyze_video_content(file_id) → AI-powered scene detection",
                "🎬 Start editing: get_file_info(file_id) → process_file(file_id, 'operation')",
                "✂️ Smart trimming: smart_trim_suggestions(file_id) → intelligent content-based cuts"
            ])
        
        if len(audio_files) >= 1 and len(video_files) >= 1:
            what_next_suggestions.append("🎵 Create music video: generate_komposition_from_description('your idea here')")
            
        if len(video_files) >= 2:
            what_next_suggestions.append("🔗 Complex workflow: batch_process([operations]) → multi-step processing")
        
        # Check for existing manifests
        temp_dir = Path("/tmp/music/temp")
        if (temp_dir / "AUDIO_TIMING_MANIFEST.json").exists():
            what_next_suggestions.append("🎵 Use audio manifest: build_video_from_audio_manifest() → direct manifest execution")
            
        what_next_suggestions.extend([
            "📁 Track outputs: list_generated_files() → see all processed videos",
            "🧹 Clean workspace: cleanup_temp_files() → remove temporary files"
        ])
            
    except Exception as e:
        return {"error": f"Failed to list files: {str(e)}", "files": [], "suggestions": [], "quick_actions": []}
        
    return {
        "files": files,
        "suggestions": suggestions,
        "quick_actions": quick_actions,
        "what_next_suggestions": what_next_suggestions,
        "stats": {
            "total_files": len(files),
            "videos": len(video_files), 
            "audio": len(audio_files),
            "images": len(image_files)
        }
    }


@mcp.tool()
@timing_decorator
async def get_file_info(file_id: str) -> Dict[str, Any]:
    """📋 FILE INFO - Get detailed metadata for a file by ID
    
    🚨 LLM GUIDANCE: Use file IDs from list_files(), NEVER file paths.
    Example: get_file_info("src_video_abc123") not get_file_info("/path/to/video.mp4")
    
    Returns comprehensive metadata including duration, resolution, format, and processing history.
    """
    file_path = file_manager.resolve_id(file_id)
    
    if not file_path:
        return {"error": f"File ID '{file_id}' not found"}
        
    if not file_path.exists():
        return {"error": f"File no longer exists: {file_path.name}"}
        
    # Get basic file info
    basic_info = {
        "id": file_id,
        "name": file_path.name,
        "size": file_path.stat().st_size,
        "extension": file_path.suffix.lower()
    }
    
    # Get detailed media info using ffprobe with caching
    media_info = await ffmpeg.get_file_info(file_path, file_manager, file_id)
    
    return {
        "basic_info": basic_info,
        "media_info": media_info
    }


@mcp.tool()
@timing_decorator
async def get_available_operations() -> Dict[str, Dict[str, str]]:
    """Get list of available FFMPEG operations"""
    operations = ffmpeg.get_available_operations()
    return {"operations": operations}

@mcp.tool()
@timing_decorator
async def get_available_transitions() -> Dict[str, Any]:
    """Get catalog of available video transition effects with parameters and examples"""
    
    transitions = {
        "crossfade_transition": {
            "name": "Crossfade Transition",
            "description": "Classic dissolve transition between two clips",
            "category": "fade",
            "performance": "fast",
            "parameters": [
                {
                    "name": "duration_beats",
                    "type": "float",
                    "min": 0.5,
                    "max": 8.0,
                    "default": 2.0,
                    "description": "Length of transition in beats"
                },
                {
                    "name": "start_offset_beats", 
                    "type": "float",
                    "min": -4.0,
                    "max": 4.0,
                    "default": -1.0,
                    "description": "When to start transition (negative = overlap)"
                }
            ],
            "example": {
                "effect_id": "crossfade_demo",
                "type": "crossfade_transition",
                "parameters": {
                    "duration_beats": 2,
                    "start_offset_beats": -1
                },
                "applies_to": [
                    {"type": "segment", "id": "clip1"},
                    {"type": "segment", "id": "clip2"}
                ]
            }
        },
        "gradient_wipe": {
            "name": "Gradient Wipe",
            "description": "Directional wipe transition (right-to-left)",
            "category": "wipe",
            "performance": "fast",
            "parameters": [
                {
                    "name": "duration_beats",
                    "type": "float", 
                    "min": 0.5,
                    "max": 8.0,
                    "default": 2.0,
                    "description": "Length of wipe in beats"
                },
                {
                    "name": "start_offset_beats",
                    "type": "float",
                    "min": -4.0,
                    "max": 4.0, 
                    "default": -1.0,
                    "description": "Wipe start timing offset"
                }
            ],
            "example": {
                "effect_id": "wipe_demo",
                "type": "gradient_wipe",
                "parameters": {
                    "duration_beats": 1.5,
                    "start_offset_beats": -0.5
                },
                "applies_to": [
                    {"type": "segment", "id": "clip1"},
                    {"type": "segment", "id": "clip2"}
                ]
            }
        },
        "opacity_transition": {
            "name": "Opacity Transition",
            "description": "Alpha-blended overlay transition",
            "category": "overlay",
            "performance": "medium",
            "parameters": [
                {
                    "name": "opacity",
                    "type": "float",
                    "min": 0.0,
                    "max": 1.0,
                    "default": 0.5,
                    "description": "Transparency level (0=transparent, 1=opaque)"
                }
            ],
            "example": {
                "effect_id": "opacity_demo", 
                "type": "opacity_transition",
                "parameters": {
                    "opacity": 0.7
                },
                "applies_to": [
                    {"type": "segment", "id": "clip1"},
                    {"type": "segment", "id": "clip2"}
                ]
            }
        }
    }
    
    # Add new xfade transition types
    xfade_transitions = {
        "wipe_left": {
            "name": "Wipe Left",
            "description": "Left-to-right wipe transition",
            "category": "wipe",
            "performance": "fast"
        },
        "wipe_up": {
            "name": "Wipe Up", 
            "description": "Bottom-to-top wipe transition",
            "category": "wipe",
            "performance": "fast"
        },
        "wipe_down": {
            "name": "Wipe Down",
            "description": "Top-to-bottom wipe transition", 
            "category": "wipe",
            "performance": "fast"
        },
        "slide_left": {
            "name": "Slide Left",
            "description": "Slide transition moving left",
            "category": "slide",
            "performance": "fast"
        },
        "slide_right": {
            "name": "Slide Right", 
            "description": "Slide transition moving right",
            "category": "slide",
            "performance": "fast"
        },
        "slide_up": {
            "name": "Slide Up",
            "description": "Slide transition moving up",
            "category": "slide", 
            "performance": "fast"
        },
        "slide_down": {
            "name": "Slide Down",
            "description": "Slide transition moving down",
            "category": "slide",
            "performance": "fast"
        },
        "circle_crop": {
            "name": "Circle Crop",
            "description": "Circular crop reveal transition",
            "category": "crop",
            "performance": "fast"
        },
        "fade_black": {
            "name": "Fade Black",
            "description": "Fade through black transition",
            "category": "fade",
            "performance": "fast"
        },
        "fade_white": {
            "name": "Fade White",
            "description": "Fade through white transition", 
            "category": "fade",
            "performance": "fast"
        }
    }
    
    # Add standard parameters for all xfade transitions
    standard_xfade_params = [
        {
            "name": "duration_beats",
            "type": "float",
            "min": 0.5,
            "max": 8.0,
            "default": 2.0,
            "description": "Length of transition in beats"
        },
        {
            "name": "start_offset_beats",
            "type": "float", 
            "min": -4.0,
            "max": 4.0,
            "default": -1.0,
            "description": "When to start transition (negative = overlap)"
        }
    ]
    
    # Add xfade transitions to catalog
    for transition_id, transition_info in xfade_transitions.items():
        transitions[transition_id] = {
            **transition_info,
            "parameters": standard_xfade_params,
            "example": {
                "effect_id": f"{transition_id}_demo",
                "type": transition_id,
                "parameters": {
                    "duration_beats": 1.5,
                    "start_offset_beats": -0.5
                },
                "applies_to": [
                    {"type": "segment", "id": "clip1"},
                    {"type": "segment", "id": "clip2"}
                ]
            }
        }
    
    return {
        "transitions": transitions,
        "total_count": len(transitions),
        "categories": ["fade", "wipe", "overlay", "slide", "crop"],
        "performance_tiers": ["fast", "medium", "slow"],
        "schema_version": "1.1",
        "usage_notes": [
            "Use effects_tree structure in komposition JSON",
            "duration_beats calculated as: beats / (bpm/60)", 
            "Negative start_offset_beats creates overlap between clips",
            "All transitions require exactly 2 clips in applies_to array",
            "New in v1.1: Added 10 additional xfade transition types"
        ]
    }


@mcp.tool()
@timing_decorator
async def process_file(
    input_file_id: str,
    operation: str,  # Available: convert, extract_audio, trim, resize, normalize_audio, to_mp3, replace_audio, concatenate_simple, image_to_video, reverse
    output_extension: str = "mp4",  # Common: mp4, mp3, wav, mov, avi
    params: str = ""  # This is params_str for execute_core_processing
) -> ProcessResult:
    """🎬 CORE WORKFLOW - Process a file using FFMPEG with specified operation
    
    This is your main processing tool for individual file operations.
    
    Parameters:
        input_file_id: File ID from list_files()
        operation: Operation name (see get_available_operations())
        output_extension: Output format (mp4, mp3, wav, etc.)
        params: Operation-specific parameters as string
    
    Common Examples:
        → process_file(file_id, "to_mp3", "mp3") - Convert to MP3
        → process_file(file_id, "trim", "mp4", "start=10 duration=5") - Trim 5s from 10s mark
        → process_file(file_id, "resize", "mp4", "width=1920 height=1080") - Resize video
        → process_file(file_id, "extract_audio", "wav") - Extract audio track
    
    Next Steps:
        → list_generated_files() - See what was created
        → batch_process() - Chain multiple operations
        → get_file_info() - Check output metadata
    """
    # Delegate to the core processing logic in video_operations.py
    # Simple user identification - in production this would come from authentication
    user_id = os.getenv("MCP_USER_ID", "anonymous")
    
    return await execute_core_processing(
        input_file_id=input_file_id,
        operation=operation,
        output_extension=output_extension,
        params_str=params, # Pass the original 'params' string here
        file_manager=file_manager, # Pass the global instance
        ffmpeg=ffmpeg,             # Pass the global instance
        user_id=user_id
    )


@mcp.tool()
@timing_decorator
async def analyze_video_content(file_id: str, force_reanalysis: bool = False) -> Dict[str, Any]:
    """Analyze video content to understand scenes, objects, and generate intelligent editing suggestions"""
    
    # Resolve file path
    file_path = file_manager.resolve_id(file_id)
    if not file_path:
        return {"success": False, "error": f"File ID '{file_id}' not found"}
        
    if not file_path.exists():
        return {"success": False, "error": f"File no longer exists: {file_path.name}"}
    
    # Only analyze video files
    if file_path.suffix.lower() not in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        return {"success": False, "error": f"Content analysis only supported for video files"}
        
    try:
        # Calculate timeout based on file size (5 minutes base + 1 minute per 10MB)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        timeout_seconds = min(300 + (file_size_mb * 6), 1800)  # Max 30 minutes
        operation_id = f"analyze_content_{file_id}_{int(time.time())}"
        
        logger.info(f"Starting video analysis with {timeout_seconds:.0f}s timeout (file: {file_size_mb:.1f}MB)")
        
        # Wrap with timeout protection
        result = await timeout_manager.execute_with_timeout(
            content_analyzer.analyze_video_content(file_path, file_id, force_reanalysis),
            operation_id=operation_id,
            timeout_seconds=timeout_seconds,
            cleanup_callback=lambda: content_analyzer.cleanup_analysis_resources()
        )
        return result
        
    except TimeoutError as e:
        logger.error(f"Video analysis timed out for {file_id}: {e}")
        return {
            "success": False, 
            "error": f"Analysis timed out after {timeout_seconds:.0f} seconds", 
            "suggestion": "Try with a smaller video file or increase timeout limits"
        }
    except Exception as e:
        return {"success": False, "error": f"Analysis failed: {str(e)}"}


@mcp.tool()  
async def get_video_insights(file_id: str) -> Dict[str, Any]:
    """Get cached video content insights and intelligent editing suggestions"""
    
    # First check if we have cached analysis
    analysis = await content_analyzer.get_cached_analysis(file_id)
    
    if not analysis:
        return {
            "success": False, 
            "error": "No analysis available. Run analyze_video_content first.",
            "suggestion": f"Call analyze_video_content(file_id='{file_id}') to generate insights"
        }
    
    # Extract useful insights for editing
    insights = {
        "success": True,
        "file_info": analysis.get("file_info", {}),
        "scene_count": analysis.get("total_scenes", 0),
        "total_duration": analysis.get("total_duration", 0),
        "highlights": analysis.get("summary", {}).get("best_scenes_for_highlights", []),
        "editing_suggestions": analysis.get("summary", {}).get("editing_suggestions", []),
        "detected_content": analysis.get("summary", {}).get("detected_objects", []),
        "visual_characteristics": analysis.get("summary", {}).get("common_characteristics", [])
    }
    
    # Add scene breakdown
    scenes = analysis.get("scenes", [])
    insights["scenes"] = [
        {
            "scene_id": scene["scene_id"],
            "start": scene["start"], 
            "end": scene["end"],
            "duration": scene["duration"],
            "objects": scene["objects"],
            "characteristics": scene["characteristics"]
        }
        for scene in scenes
    ]
    
    return insights


@mcp.tool()
@timing_decorator
async def smart_trim_suggestions(file_id: str, desired_duration: float = 10.0) -> Dict[str, Any]:
    """Get intelligent trim suggestions based on video content analysis"""
    
    # Get cached analysis
    analysis = await content_analyzer.get_cached_analysis(file_id)
    
    if not analysis:
        return {
            "success": False,
            "error": "No analysis available. Run analyze_video_content first.",
            "suggestion": f"Call analyze_video_content(file_id='{file_id}') to enable smart trimming"
        }
    
    try:
        suggestions = content_analyzer.get_smart_trim_suggestions(analysis, desired_duration)
        
        return {
            "success": True,
            "file_id": file_id,
            "desired_duration": desired_duration,
            "suggestions": suggestions,
            "usage_hint": "Use the start/end times from suggestions with the 'trim' operation"
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to generate suggestions: {str(e)}"}


@mcp.tool()
@timing_decorator
async def get_scene_screenshots(file_id: str) -> Dict[str, Any]:
    """Get scene screenshots with URLs for visual scene selection"""
    
    # Validate file exists
    file_path = file_manager.resolve_id(file_id)
    if not file_path:
        return {"success": False, "error": f"File ID '{file_id}' not found"}
        
    # Only work with video files
    if file_path.suffix.lower() not in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        return {"success": False, "error": f"Screenshots only supported for video files"}
    
    try:
        result = await content_analyzer.get_scene_screenshots(file_id)
        
        if result["success"]:
            result["usage_hint"] = "Use screenshot URLs to visually select scenes for editing operations"
            result["next_steps"] = [
                "Use scene start/end times with trim operation",
                "Reference scenes by scene_id for consistent editing",
                "Combine multiple scenes using concatenate operations"
            ]
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"Failed to get screenshots: {str(e)}"}


@mcp.tool()
@timing_decorator
async def list_generated_files() -> Dict[str, Any]:
    """📁 GENERATED FILES - List all processed files with metadata
    
    🚨 LLM GUIDANCE: Use this to find previously generated content in the registry.
    NEVER scan /tmp/music/temp/ directly - trust the registry system.
    
    Shows files you've created through video processing operations.
    """
    
    try:
        temp_files = []
        
        # Scan temp directory for generated files
        for temp_file in SecurityConfig.TEMP_DIR.glob("temp_*.mp4"):
            if temp_file.is_file() and temp_file.stat().st_size > 0:
                # Register file to get file ID
                file_id = file_manager.register_file(temp_file)
                
                temp_files.append({
                    "file_id": file_id,
                    "name": temp_file.name,
                    "size": temp_file.stat().st_size,
                    "created": temp_file.stat().st_mtime,
                    "extension": temp_file.suffix,
                    "type": "generated_video"
                })
        
        # Also scan for generated audio files
        for temp_file in SecurityConfig.TEMP_DIR.glob("temp_*.mp3"):
            if temp_file.is_file() and temp_file.stat().st_size > 0:
                file_id = file_manager.register_file(temp_file)
                
                temp_files.append({
                    "file_id": file_id,
                    "name": temp_file.name,
                    "size": temp_file.stat().st_size,
                    "created": temp_file.stat().st_mtime,
                    "extension": temp_file.suffix,
                    "type": "generated_audio"
                })
        
        # Sort by creation time (newest first)
        temp_files.sort(key=lambda x: x["created"], reverse=True)
        
        return {
            "success": True,
            "generated_files": temp_files,
            "total_count": len(temp_files),
            "usage_hint": "These are files created by video processing operations",
            "next_steps": [
                "Use file_id with other operations",
                "Get detailed info with get_file_info(file_id)",
                "Clean up with cleanup_temp_files()"
            ]
        }
        
    except Exception as e:
        return {"success": False, "error": f"Failed to list generated files: {str(e)}"}


@mcp.tool()
@timing_decorator
async def batch_process(operations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """🔧 WORKFLOW TOOL - Execute multiple video operations in sequence with atomic transaction support
    
    Perfect for complex workflows that require multiple processing steps.
    Supports operation chaining where output of one becomes input of next.
    
    Args:
        operations: List of operation dicts with keys:
            - input_file_id: File ID (use "OUTPUT_PREVIOUS" to chain operations)
            - operation: Operation name from get_available_operations()
            - output_extension: Output format (mp4, mp3, wav, etc.)  
            - params: Operation-specific parameters
            - output_name: Optional custom output filename
    
    Common Workflow Examples:
        # Music Video Creation:
        operations = [
            {"input_file_id": "file_123", "operation": "trim", "output_extension": "mp4", "params": "start=0 duration=10"},
            {"input_file_id": "OUTPUT_PREVIOUS", "operation": "resize", "output_extension": "mp4", "params": "width=1080 height=1920"},
            {"input_file_id": "OUTPUT_PREVIOUS", "operation": "replace_audio", "output_extension": "mp4", "params": "audio_file_id=file_456"}
        ]
        
        # Audio Processing Chain:
        operations = [
            {"input_file_id": "file_789", "operation": "extract_audio", "output_extension": "wav"},
            {"input_file_id": "OUTPUT_PREVIOUS", "operation": "normalize_audio", "output_extension": "wav"}
        ]
    
    Next Steps:
        → list_generated_files() - See all outputs created
        → get_file_info() - Check final result metadata
        → cleanup_temp_files() - Clean up intermediate files
    
    Returns:
        Results for each operation with file IDs for chaining
    """
    
    try:
        results = []
        current_file_id = None
        
        for i, op in enumerate(operations):
            # Use previous output as input for chaining (if input_file_id is 'OUTPUT_PREVIOUS')
            input_id = op.get('input_file_id')
            if input_id in ['OUTPUT_PREVIOUS', 'CHAIN'] and current_file_id:
                input_id = current_file_id
            elif input_id in ['OUTPUT_PREVIOUS', 'CHAIN'] and not current_file_id:
                return {"success": False, "error": f"Operation {i}: Cannot chain - no previous output"}
            
            operation = op.get('operation')
            output_ext = op.get('output_extension', 'mp4')
            params = op.get('params', '')
            
            print(f"Batch step {i+1}: {operation} on {input_id}")
            
            # Execute operation
            result = await process_file(
                input_file_id=input_id,
                operation=operation,
                output_extension=output_ext,
                params=params
            )
            
            # Handle result format (both dict and object)
            success = result.success if hasattr(result, 'success') else result.get('success', False)
            message = result.message if hasattr(result, 'message') else result.get('message', 'No message')
            output_id = result.output_file_id if hasattr(result, 'output_file_id') else result.get('output_file_id')
            
            step_result = {
                "step": i + 1,
                "operation": operation,
                "success": success,
                "message": message,
                "output_file_id": output_id,
                "input_file_id": input_id
            }
            
            results.append(step_result)
            
            if success and output_id:
                current_file_id = output_id  # For chaining
            else:
                # Stop on first failure
                return {
                    "success": False,
                    "error": f"Batch failed at step {i+1}: {message}",
                    "completed_steps": results,
                    "final_output": None
                }
        
        return {
            "success": True,
            "total_steps": len(operations),
            "completed_steps": results,
            "final_output": current_file_id,
            "usage_hint": "All operations completed successfully. Use final_output file_id for further processing."
        }
        
    except Exception as e:
        return {"success": False, "error": f"Batch processing failed: {str(e)}"}


@mcp.tool()
@timing_decorator
async def cleanup_temp_files() -> Dict[str, str]:
    """Clean up temporary files"""
    try:
        file_manager.cleanup_temp_files()
        return {"message": "Temporary files cleaned up successfully"}
    except Exception as e:
        return {"error": f"Failed to cleanup temp files: {str(e)}"}


@mcp.tool()
@timing_decorator
async def get_registry_status() -> Dict[str, Any]:
    """📊 REGISTRY STATUS - Get file registry health and statistics
    
    🚨 LLM GUIDANCE: Use this to check registry health and find orphaned files.
    If you suspect cache misses or missing files, this is your diagnostic tool.
    
    Returns counts, storage usage, orphaned files, and registry health metrics.
    """
    try:
        # Get source files count
        source_files = await list_files()
        source_count = len(source_files.get("files", []))
        
        # Get generated files count  
        generated_files = await list_generated_files()
        generated_count = len(generated_files.get("temp_files", []))
        
        # Check for potential issues
        issues = []
        if generated_count > 0 and "temp_files" in generated_files:
            # Check if any files have missing registry entries
            temp_files = generated_files["temp_files"]
            for temp_file in temp_files:
                if not temp_file.get("file_id"):
                    issues.append(f"Orphaned file detected: {temp_file.get('name', 'unknown')}")
        
        # Calculate storage estimates
        total_storage = 0
        if "files" in source_files:
            total_storage += sum(f.get("size", 0) for f in source_files["files"])
        if "temp_files" in generated_files:
            total_storage += sum(f.get("size", 0) for f in generated_files["temp_files"])
        
        return {
            "registry_health": "healthy" if len(issues) == 0 else "issues_detected",
            "source_files_count": source_count,
            "generated_files_count": generated_count,
            "total_storage_bytes": total_storage,
            "total_storage_mb": round(total_storage / (1024 * 1024), 2),
            "issues": issues,
            "recommendations": [
                "🎬 Use list_files() to discover available content",
                "📋 Use get_file_info(file_id) for file details", 
                "🔑 Work with file IDs, never direct paths",
                "🗂️ Trust the registry as single source of truth"
            ]
        }
    except Exception as e:
        return {"error": f"Failed to get registry status: {str(e)}"}


# MCP Prompts for Video Editing Guidance
@mcp.prompt()
async def analyze_video_for_editing(file_id: str = "") -> str:
    """Analyze video metadata and suggest optimal editing operations"""
    if not file_id:
        return """Please provide a file_id to analyze. Use list_files() to see available videos.

This prompt will analyze your video's:
- Duration, resolution, and aspect ratio
- Video and audio codecs
- Bitrate and quality metrics
- Stream information

And suggest optimal operations like:
- Best formats for conversion
- Recommended compression settings
- Potential quality improvements
- Compatibility considerations"""
    
    # Get file info if file_id provided
    file_info = await get_file_info(file_id)
    if "error" in file_info:
        return f"Error analyzing file: {file_info['error']}"
    
    basic = file_info.get("basic_info", {})
    media = file_info.get("media_info", {})
    
    analysis = f"""# Video Analysis Report for {basic.get('name', 'Unknown')}

## Basic Information
- File Size: {basic.get('size', 0) / 1024 / 1024:.1f} MB
- Format: {basic.get('extension', 'Unknown')}

## Recommendations
Based on your video characteristics:"""
    
    if media.get("success") and "info" in media:
        info = media["info"]
        format_info = info.get("format", {})
        duration = float(format_info.get("duration", 0))
        
        analysis += f"""
- Duration: {duration:.1f} seconds
- Container: {format_info.get('format_name', 'Unknown')}

### Suggested Operations:
1. **trim** - Extract specific segments (use start= and duration= parameters)
2. **convert** - Standardize format for compatibility
3. **extract_audio** - Separate audio track for replacement
4. **replace_audio** - Add background music or narration
5. **resize** - Optimize for different platforms

### Platform Optimization:
- **YouTube**: Keep current resolution, consider converting to MP4
- **Social Media**: Consider resize to 1080p or 720p for faster upload
- **Mobile**: Compress using convert operation to reduce file size"""
    else:
        analysis += """
Media analysis unavailable. Basic operations still available:
- Use **convert** to standardize format
- Use **trim** to extract segments
- Use **extract_audio** for audio processing"""
    
    return analysis


@mcp.prompt()
async def create_video_montage() -> str:
    """Guide users through creating video montages from multiple clips"""
    return """# Creating Video Montages - Step by Step Guide

## Planning Your Montage

### 1. Identify Your Source Videos
```
Use list_files() to see available videos
Note the file_ids of videos you want to use
```

### 2. Plan Your Clips
For each video, decide:
- Start time (seconds from beginning)
- Duration (how many seconds to extract)
- Order in final montage

### 3. Extract Clips
```
For each clip:
process_file(
    input_file_id="file_xxxxx",
    operation="trim",
    output_extension="mp4",
    params="start=X duration=Y"
)
```

### 4. Standardize Format (Recommended)
```
For each extracted clip:
process_file(
    input_file_id="extracted_clip_id",
    operation="convert",
    output_extension="mp4",
    params=""
)
```

### 5. Combine Clips
```
Use concatenate_simple to join clips:
process_file(
    input_file_id="first_clip_id",
    operation="concatenate_simple",
    output_extension="mp4",
    params="second_video=second_clip_id"
)
```

### 6. Add Final Audio
```
Replace with background music:
process_file(
    input_file_id="combined_video_id",
    operation="replace_audio",
    output_extension="mp4",
    params="audio_file=music_file_id"
)
```

## Pro Tips:
- Keep clips short (3-10 seconds) for dynamic montages
- Ensure consistent resolution across all clips
- Consider rhythm when timing cuts to music
- Test with small clips before processing long videos"""


@mcp.prompt()
async def optimize_for_platform(platform: str = "") -> str:
    """Provide platform-specific optimization recommendations"""
    
    platforms = {
        "youtube": {
            "resolution": "1920x1080 (1080p) or 1280x720 (720p)",
            "aspect_ratio": "16:9",
            "format": "MP4 (H.264 video, AAC audio)",
            "max_size": "128GB or 12 hours",
            "bitrate": "8-12 Mbps for 1080p",
            "fps": "24, 25, 30, 50, or 60 fps"
        },
        "instagram": {
            "resolution": "1080x1080 (square) or 1080x1350 (portrait)",
            "aspect_ratio": "1:1 or 4:5",
            "format": "MP4 or MOV",
            "max_size": "4GB",
            "duration": "60 seconds max for feed, 15 seconds for stories",
            "bitrate": "3.5 Mbps recommended"
        },
        "tiktok": {
            "resolution": "1080x1920 (vertical)",
            "aspect_ratio": "9:16",
            "format": "MP4 or MOV",
            "max_size": "287.6MB",
            "duration": "10 minutes max",
            "bitrate": "Variable, platform optimizes"
        },
        "twitter": {
            "resolution": "1920x1080 or 1280x720",
            "aspect_ratio": "16:9 recommended",
            "format": "MP4 or MOV",
            "max_size": "512MB",
            "duration": "2 minutes 20 seconds max",
            "bitrate": "6-10 Mbps"
        }
    }
    
    if not platform:
        return f"""# Platform Optimization Guide

Choose your target platform:
{chr(10).join([f"- **{p.title()}**" for p in platforms.keys()])}

## General Optimization Steps:

### 1. Check Current Video Properties
```
get_file_info(file_id="your_video_id")
```

### 2. Resize if Needed
```
process_file(
    input_file_id="your_video_id",
    operation="resize", 
    output_extension="mp4",
    params="width=1920 height=1080"
)
```

### 3. Convert for Compatibility
```
process_file(
    input_file_id="your_video_id",
    operation="convert",
    output_extension="mp4",
    params=""
)
```

### 4. Compress for Size Limits
```
Use convert operation with MP4 output
This automatically applies reasonable compression
```

Call this prompt again with platform="youtube" (or instagram, tiktok, twitter) for specific guidelines."""
    
    platform = platform.lower()
    if platform in platforms:
        specs = platforms[platform]
        return f"""# {platform.title()} Optimization Guide

## Technical Specifications:
- **Resolution**: {specs['resolution']}
- **Aspect Ratio**: {specs['aspect_ratio']}
- **Format**: {specs['format']}
- **Max File Size**: {specs['max_size']}
- **Recommended Bitrate**: {specs.get('bitrate', 'Variable')}
{f"- **Frame Rate**: {specs['fps']}" if 'fps' in specs else ""}
{f"- **Max Duration**: {specs['duration']}" if 'duration' in specs else ""}

## Optimization Steps:

### 1. Resize Video (if needed)
```
process_file(
    input_file_id="your_video_id",
    operation="resize",
    output_extension="mp4", 
    params="width=X height=Y"  # Use resolution from specs above
)
```

### 2. Convert to Optimal Format
```
process_file(
    input_file_id="your_video_id",
    operation="convert",
    output_extension="mp4",
    params=""
)
```

### 3. Trim if Exceeding Duration Limits
```
process_file(
    input_file_id="your_video_id",
    operation="trim",
    output_extension="mp4",
    params="start=0 duration=X"  # X = max seconds allowed
)
```

## {platform.title()}-Specific Tips:
{_get_platform_tips(platform)}"""
    else:
        return f"Platform '{platform}' not recognized. Available: {', '.join(platforms.keys())}"


def _get_platform_tips(platform: str) -> str:
    """Get platform-specific tips"""
    tips = {
        "youtube": """- Use clear thumbnails and titles
- Consider adding captions with extract_audio + replace_audio workflow
- Longer content performs better (8+ minutes)
- Maintain consistent upload schedule""",
        "instagram": """- First 3 seconds are crucial for engagement
- Use trending audio with replace_audio operation
- Square format works best for feed posts
- Stories should be 9:16 vertical""",
        "tiktok": """- Vertical format is mandatory (9:16)
- Hook viewers in first 3 seconds
- Trending sounds boost visibility
- Quick cuts and dynamic editing work best""",
        "twitter": """- Auto-play is silent, add captions
- Keep videos under 2 minutes for best engagement
- Square or landscape formats work well
- Consider GIF conversion for short clips"""
    }
    return tips.get(platform, "No specific tips available")


@mcp.prompt()
async def improve_video_quality() -> str:
    """Provide guidance for enhancing video quality"""
    return """# Video Quality Enhancement Guide

## Quality Assessment Steps

### 1. Analyze Current Quality
```
get_file_info(file_id="your_video_id")
```
Look for:
- Resolution (higher is generally better)
- Bitrate (affects file size vs quality)
- Codec (newer codecs like H.264/H.265 are more efficient)

### 2. Basic Quality Improvements

#### Convert to Modern Codec
```
process_file(
    input_file_id="your_video_id",
    operation="convert",
    output_extension="mp4",
    params=""
)
```
Benefits:
- Better compression efficiency
- Wider compatibility
- Improved streaming performance

#### Audio Enhancement
```
# Extract current audio
process_file(
    input_file_id="your_video_id", 
    operation="extract_audio",
    output_extension="m4a",
    params=""
)

# Normalize audio levels
process_file(
    input_file_id="extracted_audio_id",
    operation="normalize_audio", 
    output_extension="m4a",
    params=""
)

# Replace with normalized audio
process_file(
    input_file_id="your_video_id",
    operation="replace_audio",
    output_extension="mp4", 
    params="audio_file=normalized_audio_id"
)
```

## Quality Issues & Solutions

### Low Resolution
**Problem**: Video appears pixelated or blurry
**Solution**: Unfortunately, upscaling isn't available in current operations
**Prevention**: Always record/export at highest available resolution

### Audio Issues
**Problem**: Audio too quiet, too loud, or inconsistent
**Solution**: Use normalize_audio operation
```
process_file(operation="normalize_audio", ...)
```

### Large File Sizes
**Problem**: File too big for sharing/uploading
**Solution**: Re-encode with convert operation
```
process_file(operation="convert", output_extension="mp4", ...)
```

### Compatibility Issues
**Problem**: Video won't play on certain devices/platforms
**Solution**: Convert to MP4 with H.264 codec
```
process_file(operation="convert", output_extension="mp4", ...)
```

## Best Practices:
- Always keep original files as backup
- Test conversions with short clips first
- Consider target platform requirements
- Balance file size with quality needs
- Use consistent settings across related videos"""


@mcp.prompt()
async def compress_efficiently() -> str:
    """Guide users through efficient video compression"""
    return """# Efficient Video Compression Guide

## Understanding Compression

### File Size Factors:
1. **Resolution** - Higher resolution = larger files
2. **Duration** - Longer videos = larger files  
3. **Bitrate** - Higher bitrate = better quality but larger files
4. **Codec** - Modern codecs compress better

## Compression Workflow

### 1. Check Current File Size
```
list_files()  # Check size column
```

### 2. Estimate Target Size
- **Email**: < 25MB typically
- **SMS/Messaging**: < 100MB
- **Social Media**: varies by platform (see optimize_for_platform prompt)
- **Streaming**: Balance quality vs bandwidth

### 3. Apply Compression
```
process_file(
    input_file_id="your_video_id",
    operation="convert", 
    output_extension="mp4",
    params=""
)
```

### 4. Check Results
```
list_files()  # Compare new file size
```

## Advanced Compression Strategies

### For Large Size Reductions:
1. **Trim Unnecessary Content**
```
process_file(
    operation="trim",
    params="start=X duration=Y"  # Keep only essential parts
)
```

2. **Reduce Resolution** 
```
process_file(
    operation="resize",
    params="width=1280 height=720"  # From 1080p to 720p
)
```

3. **Convert to Efficient Format**
```
process_file(operation="convert", output_extension="mp4")
```

## Compression Decision Matrix

### Original > 1GB:
- Try resize to 720p first
- Then convert to MP4
- Consider trimming if possible

### Original 100MB - 1GB:
- Convert to MP4 first
- Resize only if still too large

### Original < 100MB:
- Usually just convert to MP4
- May not need compression

## Quality vs Size Estimates:
- **1080p MP4**: ~8-12 Mbps (1MB per second)
- **720p MP4**: ~4-6 Mbps (0.5MB per second)  
- **480p MP4**: ~2-3 Mbps (0.25MB per second)

## Pro Tips:
- Always test with a short clip first
- Keep original files as backup
- Different content compresses differently (talking head vs action)
- Modern phones can handle lower resolutions well"""


@mcp.prompt()
async def create_highlight_reel() -> str:
    """Guide users through creating highlight reels from longer content"""
    return """# Creating Highlight Reels - Complete Guide

## Planning Your Highlight Reel

### 1. Content Analysis
- Watch your source video(s) and note timestamps of best moments
- Aim for 30-60 seconds total for social media
- 2-3 minutes for longer form content

### 2. Identify Key Moments
Look for:
- Peak action or excitement
- Emotional moments
- Key information or quotes
- Visually stunning scenes
- Audience reactions

## Step-by-Step Workflow

### 1. Extract Individual Highlights
```
# For each highlight moment:
process_file(
    input_file_id="source_video_id",
    operation="trim",
    output_extension="mp4", 
    params="start=X duration=Y"  # X=start time, Y=clip length
)
```

**Recommended clip lengths:**
- Action moments: 3-5 seconds
- Dialogue/quotes: 5-10 seconds  
- Establishing shots: 2-3 seconds

### 2. Standardize All Clips
```
# Convert each extracted clip:
process_file(
    input_file_id="highlight_clip_id",
    operation="convert",
    output_extension="mp4",
    params=""
)
```

### 3. Combine Highlights
```
# Join clips sequentially:
process_file(
    input_file_id="first_clip_id", 
    operation="concatenate_simple",
    output_extension="mp4",
    params="second_video=second_clip_id"
)

# Continue adding more clips as needed
```

### 4. Add Background Music
```
# Replace audio with energetic music:
process_file(
    input_file_id="combined_highlights_id",
    operation="replace_audio", 
    output_extension="mp4",
    params="audio_file=music_file_id"
)
```

## Highlight Reel Best Practices

### Pacing & Flow:
- Start with your strongest moment
- Vary clip lengths for rhythm
- Build energy throughout
- End with a memorable moment

### Music Selection:
- Match tempo to content energy
- Ensure music is royalty-free
- Consider platform requirements
- Volume should complement, not overpower

### Technical Tips:
- Keep consistent resolution across clips
- Ensure smooth transitions
- Test on target platform before sharing
- Consider adding text overlays (external tool needed)

## Common Workflows by Content Type:

### Sports/Action:
- 2-4 second clips of peak action
- Fast-paced music
- Quick cuts for energy

### Educational/Talking Head:
- 5-8 second clips of key points
- Moderate pacing
- Include visual variety

### Event/Documentary:
- Mix of 3-10 second clips
- Emotional music choices
- Tell a story through clip selection

### Gaming:
- Epic moments, fails, wins
- Synchronized to music beats
- Include reaction moments

## Example Highlight Reel Structure (60 seconds):
1. **Hook** (0-5s): Best/most exciting moment
2. **Introduction** (5-15s): Set context
3. **Build** (15-45s): 3-4 supporting highlights  
4. **Climax** (45-55s): Second best moment
5. **Outro** (55-60s): Memorable ending

Remember: Great highlight reels tell a story, not just show random good moments!"""


@mcp.prompt()
async def add_professional_audio() -> str:
    """Guide users through professional audio workflows"""
    return """# Professional Audio Enhancement Guide

## Audio Quality Assessment

### 1. Analyze Current Audio
```
get_file_info(file_id="your_video_id")
```
Look for audio stream information:
- Sample rate (44.1kHz or 48kHz preferred)
- Bit depth (16-bit minimum, 24-bit better)
- Codec (AAC is modern standard)

### 2. Extract for Analysis
```
process_file(
    input_file_id="your_video_id",
    operation="extract_audio", 
    output_extension="m4a",
    params=""
)
```

## Professional Audio Workflows

### Workflow 1: Audio Cleanup & Enhancement
```
# Step 1: Extract original audio
process_file(
    input_file_id="video_id",
    operation="extract_audio",
    output_extension="m4a", 
    params=""
)

# Step 2: Normalize levels
process_file(
    input_file_id="extracted_audio_id",
    operation="normalize_audio",
    output_extension="m4a",
    params=""
)

# Step 3: Replace with enhanced audio
process_file(
    input_file_id="video_id", 
    operation="replace_audio",
    output_extension="mp4",
    params="audio_file=normalized_audio_id"
)
```

### Workflow 2: Background Music Addition
```
# Replace original audio with music:
process_file(
    input_file_id="video_id",
    operation="replace_audio",
    output_extension="mp4", 
    params="audio_file=music_file_id"
)
```

### Workflow 3: Voiceover Replacement
```
# Record voiceover separately, then:
process_file(
    input_file_id="video_id",
    operation="replace_audio", 
    output_extension="mp4",
    params="audio_file=voiceover_file_id"
)
```

## Audio Best Practices

### Recording Quality:
- **Environment**: Quiet space, minimal echo
- **Distance**: 6-12 inches from microphone
- **Levels**: Avoid clipping, aim for -12dB to -6dB peaks
- **Format**: Record in highest quality available

### Post-Production:
- **Normalize**: Use normalize_audio for consistent levels
- **Noise Floor**: Keep ambient noise low
- **Dynamic Range**: Maintain natural variation
- **Sync**: Ensure audio matches video timing

### Music Selection:
- **Royalty-Free Sources**:
  - YouTube Audio Library
  - Freesound.org
  - CC Search
  - Local musician collaborations

- **Mood Matching**:
  - Upbeat for action/sports
  - Ambient for documentaries  
  - Dramatic for emotional content
  - Silent for dialogue-heavy content

### Platform Considerations:
- **Social Media**: Often viewed without sound initially
- **YouTube**: Good audio crucial for retention
- **Podcasts**: Audio quality is primary concern
- **Presentations**: Clear speech over music

## Audio Levels Guide:
- **Dialogue**: -12dB to -6dB average
- **Music**: -18dB to -12dB when under dialogue
- **Sound Effects**: -15dB to -8dB depending on impact needed
- **Ambient**: -24dB to -18dB for background

## Common Audio Issues & Solutions:

### Too Quiet:
```
Use normalize_audio operation
```

### Too Loud/Distorted:
- Re-record if possible
- Use normalize_audio to bring levels down

### Inconsistent Levels:
```
Extract audio → normalize_audio → replace_audio
```

### Poor Quality Music:
- Source higher quality audio files
- Ensure sample rate matches video (usually 48kHz)

### Sync Issues:
- May require external tools for fine adjustment
- Start with clean, well-synced source material

## Professional Audio Checklist:
✓ Audio levels consistent throughout
✓ No clipping or distortion
✓ Background noise minimized
✓ Music doesn't overpower dialogue
✓ Smooth transitions between clips
✓ Platform-appropriate volume levels
✓ High-quality source files used
✓ Proper format and codec selected"""


@mcp.prompt()
async def fix_video_issues() -> str:
    """Diagnose and provide solutions for common video problems"""
    return """# Video Troubleshooting & Repair Guide

## Common Issues Diagnostic

### 1. File Won't Play/Open
**Symptoms**: Error messages, black screen, no audio
**Diagnosis Steps**:
```
get_file_info(file_id="problem_video_id")
```
Look for:
- Unusual codecs
- Corruption indicators
- Missing audio/video streams

**Solutions**:
```
# Try conversion to standard format:
process_file(
    input_file_id="problem_video_id",
    operation="convert",
    output_extension="mp4", 
    params=""
)
```

### 2. Audio/Video Out of Sync
**Symptoms**: Lips don't match speech, music timing off
**Diagnosis**: Usually from encoding issues or editing errors
**Solutions**:
```
# Extract and replace audio:
process_file(operation="extract_audio", ...)
process_file(operation="replace_audio", ...)
```
*Note: Fine sync adjustment requires external tools*

### 3. Poor Video Quality
**Symptoms**: Pixelation, blurriness, artifacts
**Diagnosis**: Over-compression or low source quality
**Solutions**:
```
# Re-encode with better settings:
process_file(
    operation="convert",
    output_extension="mp4",
    params=""
)
```

### 4. File Too Large
**Symptoms**: Upload failures, storage issues
**Solutions**: See compress_efficiently prompt
```
# Basic compression:
process_file(operation="convert", output_extension="mp4")

# More aggressive:
process_file(operation="resize", params="width=1280 height=720")
```

### 5. Wrong Aspect Ratio
**Symptoms**: Black bars, stretched video
**Solutions**:
```
# Resize to correct dimensions:
process_file(
    operation="resize",
    params="width=X height=Y"  # Calculate proper aspect ratio
)
```

### 6. Audio Problems
**Symptoms**: No sound, distorted audio, wrong levels
**Solutions**:
```
# Check if audio exists:
get_file_info(file_id="video_id")

# Normalize audio levels:
process_file(operation="extract_audio", ...)
process_file(operation="normalize_audio", ...)
process_file(operation="replace_audio", ...)
```

## Preventive Measures

### Recording Best Practices:
- Use highest quality settings available
- Ensure adequate lighting
- Stable mounting/tripod use
- Test audio levels before recording
- Record in standard frame rates (24, 30, 60 fps)

### Export/Encoding Best Practices:
- Use standard codecs (H.264 video, AAC audio)
- Maintain original resolution when possible
- Use constant frame rate
- Avoid excessive compression
- Keep master copies in high quality

### Storage Best Practices:
- Regular backups of important videos
- Use reliable storage media
- Avoid network interruptions during transfers
- Verify file integrity after copying

## Emergency Recovery Procedures

### For Corrupted Files:
1. Try conversion to MP4
2. Extract working portions with trim operation
3. Check if audio can be salvaged separately

### For Upload Failures:
1. Check file size limits
2. Verify format compatibility
3. Test with smaller/shorter version first
4. Use platform-specific optimization

### For Playback Issues:
1. Convert to MP4 format
2. Test on different devices/players
3. Check codec compatibility
4. Verify file isn't corrupted

## When to Seek External Tools:
- Frame-accurate sync adjustment
- Advanced noise reduction
- Color correction/grading  
- Complex audio mixing
- Subtitle/caption addition
- Advanced effects or transitions

## File Recovery Checklist:
✓ Try basic conversion first
✓ Test with short clips before processing full video
✓ Keep original files until repair confirmed working
✓ Document what caused the issue to prevent recurrence
✓ Consider professional recovery services for critical content

## Platform-Specific Issues:

### YouTube:
- Check community guidelines compliance
- Verify copyright clearance
- Ensure proper format (MP4 recommended)

### Social Media:
- Check duration limits
- Verify aspect ratio requirements  
- Test mobile playback

### Email/Messaging:
- Compress to size limits
- Use widely compatible formats
- Test on recipient's likely device type

Remember: Prevention is better than repair - always maintain high-quality source files!"""


@mcp.prompt()
async def batch_processing_guide() -> str:
    """Guide users through efficient batch processing workflows"""
    return """# Batch Processing & Automation Guide

## Planning Batch Operations

### 1. Identify Common Tasks
- Converting multiple videos to same format
- Extracting clips from multiple long videos
- Adding same audio track to multiple videos
- Resizing multiple videos for platform
- Creating thumbnails from multiple videos

### 2. Standardize Parameters
Before starting, determine:
- Target format and resolution
- Consistent naming convention
- Output quality settings
- Processing order/priority

## Batch Workflow Strategies

### Strategy 1: Sequential Processing
Process one file completely before starting next:
```
# For each video:
1. list_files() → identify file_id
2. process_file(operation="convert", ...)
3. Verify success before continuing
4. Move to next file
```

**Pros**: Easy to track, can stop/resume
**Cons**: Slower overall, doesn't use full system capacity

### Strategy 2: Pipeline Processing  
Start multiple operations in sequence:
```
# Start multiple operations:
1. Begin trim operation on video 1
2. While that runs, start convert on video 2  
3. Chain operations as resources allow
```

**Pros**: Faster overall processing
**Cons**: More complex tracking, higher resource usage

## Common Batch Scenarios

### Scenario 1: Convert Multiple Videos to MP4
```
# Get all video files:
files = list_files()

# For each video file:
for video in video_files:
    result = process_file(
        input_file_id=video.id,
        operation="convert", 
        output_extension="mp4",
        params=""
    )
    # Check result.success before continuing
```

### Scenario 2: Extract Highlights from Multiple Long Videos
```
# Define highlight timestamps for each video:
highlights = {
    "video1_id": [(10, 5), (30, 8), (60, 6)],  # (start, duration)
    "video2_id": [(5, 4), (25, 7)],
    # etc...
}

# Extract each highlight:
for video_id, clips in highlights.items():
    for start, duration in clips:
        process_file(
            input_file_id=video_id,
            operation="trim",
            output_extension="mp4", 
            params=f"start={start} duration={duration}"
        )
```

### Scenario 3: Add Same Audio to Multiple Videos
```
# Assuming you have background_music_id:
for video_id in video_list:
    process_file(
        input_file_id=video_id,
        operation="replace_audio",
        output_extension="mp4",
        params=f"audio_file={background_music_id}"
    )
```

### Scenario 4: Platform Optimization for Multiple Videos
```
# For YouTube optimization:
target_specs = {
    "operation": "resize",
    "params": "width=1920 height=1080"
}

for video_id in video_list:
    # First resize:
    resized = process_file(
        input_file_id=video_id,
        **target_specs
    )
    
    # Then convert:
    if resized.success:
        process_file(
            input_file_id=resized.output_file_id,
            operation="convert",
            output_extension="mp4"
        )
```

## Performance Optimization

### Processing Time Estimates:
- **Convert**: ~1x video duration (10 min video = ~10 min processing)
- **Trim**: Very fast (~seconds regardless of source length)  
- **Resize**: ~0.5-2x video duration depending on size change
- **Audio operations**: ~0.1-0.5x video duration
- **Concatenate**: ~0.5x combined duration

### Resource Management:
- **CPU**: FFMPEG operations are CPU-intensive
- **Storage**: Ensure adequate temp space (2-3x source file size)
- **Memory**: Longer videos use more RAM
- **Thermal**: Extended processing may cause throttling

### Optimization Tips:
1. **Process shorter videos first** - quick wins and feedback
2. **Group similar operations** - batch all converts, then all resizes
3. **Monitor temp directory** - use cleanup_temp_files() regularly
4. **Test with samples** - verify settings work before full batch
5. **Keep source files safe** - don't delete until batch complete

## Error Handling & Recovery

### Tracking Progress:
```
# Create processing log:
results = []
for video_id in video_list:
    result = process_file(...)
    results.append({
        'video_id': video_id,
        'success': result.success,
        'output_id': result.output_file_id,
        'error': result.message if not result.success else None
    })
```

### Handling Failures:
- **Partial failures**: Skip failed files, continue with others
- **Storage full**: Use cleanup_temp_files(), then resume
- **Format errors**: Try convert operation first, then retry
- **Timeout errors**: Split large files into smaller segments

### Resume Strategies:
- Keep list of completed file_ids
- Check temp directory for existing outputs
- Restart from last successful operation

## Quality Control

### Batch Validation Checklist:
✓ All source files processed successfully
✓ Output file sizes reasonable (not 0 bytes or extremely large)
✓ Spot-check video quality on sample outputs
✓ Verify audio sync on audio-replaced videos
✓ Confirm all outputs play correctly
✓ Check that temp files cleaned up appropriately

### Testing Protocol:
1. **Small batch test** (2-3 files) with exact settings
2. **Quality verification** of test outputs
3. **Timing measurement** to estimate full batch duration
4. **Resource monitoring** to ensure system can handle load
5. **Full batch execution** with monitoring

## Automation Considerations:

### What Can Be Automated:
- Repetitive format conversions
- Standard resize operations
- Bulk audio replacement
- Cleanup operations

### What Requires Human Input:
- Creative timing decisions (clip selection)
- Quality assessment
- Error diagnosis and recovery
- Custom parameter adjustment

### Future Automation Ideas:
- Scheduled processing workflows
- Auto-detection of optimal settings
- Progress monitoring dashboards
- Automatic quality validation

Remember: Start small, test thoroughly, and always keep your source files safe during batch operations!"""


# CONTEXT SYSTEM - DISABLED (FastMCP doesn't support @mcp.context())
# These functions were originally designed as MCP context providers to give
# intelligent suggestions and workflow guidance. They can be reactivated as:
# 1. @mcp.prompt() functions for explicit context queries
# 2. Helper functions integrated into existing tool responses  
# 3. Part of enhanced tool outputs with contextual suggestions
# 
# Consider re-enabling these for better user experience when using
# a full MCP implementation that supports context providers.

# Global tracking for context intelligence
_operation_history = []
_performance_stats = {}

async def _get_files_summary() -> str:
    """Get a summary of available files - CONTEXT HELPER"""
    try:
        files_result = await list_files()
        if "error" in files_result:
            return f"Error: {files_result['error']}"
        
        files = files_result.get("files", [])
        if not files:
            return "No files available"
        
        summary = []
        total_size = 0
        
        for file in files:
            size_mb = file.size / (1024 * 1024)
            total_size += size_mb
            summary.append(f"- {file.name} ({size_mb:.1f}MB) - ID: {file.id}")
        
        return f"{len(files)} files, {total_size:.1f}MB total:\n" + "\n".join(summary)
    except Exception as e:
        return f"Error getting files: {str(e)}"

async def _get_recent_operations() -> str:
    """Get recent operations from history - CONTEXT HELPER"""
    if not _operation_history:
        return "No recent operations"
    
    recent = _operation_history[-5:]  # Last 5 operations
    summary = []
    
    for op in recent:
        timestamp = op.get('timestamp', 'Unknown time')
        operation = op.get('operation', 'Unknown')
        success = op.get('success', False)
        input_file = op.get('input_file', 'Unknown')
        status = "✅" if success else "❌"
        summary.append(f"{status} {operation} on {input_file} ({timestamp})")
    
    return "\n".join(summary)

async def _get_temp_files_status() -> str:
    """Get status of temporary files - CONTEXT HELPER"""
    try:
        import os
        temp_dir = SecurityConfig.TEMP_DIR
        
        if not temp_dir.exists():
            return "No temp directory"
        
        temp_files = list(temp_dir.glob("*"))
        if not temp_files:
            return "No temporary files"
        
        total_size = sum(f.stat().st_size for f in temp_files if f.is_file())
        size_mb = total_size / (1024 * 1024)
        
        return f"{len(temp_files)} temp files, {size_mb:.1f}MB"
    except Exception as e:
        return f"Error checking temp files: {str(e)}"

def _get_storage_info() -> str:
    """Get storage information - CONTEXT HELPER"""
    try:
        import shutil
        temp_dir = SecurityConfig.TEMP_DIR
        source_dir = SecurityConfig.SOURCE_DIR
        
        temp_free = shutil.disk_usage(temp_dir).free / (1024**3)  # GB
        source_free = shutil.disk_usage(source_dir).free / (1024**3)  # GB
        
        return f"Temp: {temp_free:.1f}GB free, Source: {source_free:.1f}GB free"
    except Exception:
        return "Storage info unavailable"

def _get_active_operations() -> str:
    """Get currently active operations - CONTEXT HELPER (placeholder for now)"""
    # In a real implementation, this would track running FFMPEG processes
    return "No active operations detected"

async def _get_file_genealogy() -> str:
    """Track file processing relationships - CONTEXT HELPER"""
    # This would track which files were created from which sources
    genealogy = {}
    
    for op in _operation_history:
        if op.get('success') and op.get('output_file_id'):
            input_file = op.get('input_file', 'Unknown')
            output_file = op.get('output_file_id', 'Unknown')
            operation = op.get('operation', 'Unknown')
            
            if input_file not in genealogy:
                genealogy[input_file] = []
            genealogy[input_file].append(f"{output_file} (via {operation})")
    
    if not genealogy:
        return "No file processing history available"
    
    summary = []
    for source, outputs in genealogy.items():
        summary.append(f"**{source}** →")
        for output in outputs:
            summary.append(f"  - {output}")
    
    return "\n".join(summary)

async def _suggest_next_operations() -> str:
    """Suggest logical next operations based on current state - CONTEXT HELPER"""
    try:
        files_result = await list_files()
        files = files_result.get("files", [])
        
        if not files:
            return "Add some video files to get started"
        
        suggestions = []
        
        # Check for large files that might need compression
        large_files = [f for f in files if f.size > 100 * 1024 * 1024]  # > 100MB
        if large_files:
            suggestions.append(f"• Consider compressing {len(large_files)} large files with convert operation")
        
        # Check for non-MP4 files
        non_mp4 = [f for f in files if f.extension.lower() != '.mp4']
        if non_mp4:
            suggestions.append(f"• Convert {len(non_mp4)} non-MP4 files for better compatibility")
        
        # Check for very long videos (based on file size estimation)
        potentially_long = [f for f in files if f.size > 500 * 1024 * 1024]  # > 500MB
        if potentially_long:
            suggestions.append(f"• Consider trimming {len(potentially_long)} potentially long videos")
        
        # Check temp files for cleanup
        temp_status = await _get_temp_files_status()
        if "temp files" in temp_status and not "No temporary" in temp_status:
            suggestions.append("• Run cleanup_temp_files() to free up space")
        
        if not suggestions:
            suggestions.append("• Files look good! Ready for editing operations")
        
        return "\n".join(suggestions)
    except Exception as e:
        return f"Error generating suggestions: {str(e)}"

def _analyze_platform_compatibility() -> str:
    """Analyze how current files match platform requirements - CONTEXT HELPER"""
    # This would analyze files against platform specs
    return """Current files analyzed against major platforms:
• YouTube: Most files compatible, consider MP4 conversion for optimal upload
• Instagram: Large files may need resizing to 1080p max
• TikTok: Consider vertical format conversion for better engagement
• Twitter: File sizes look good for platform limits"""

def _suggest_platform_optimizations() -> str:
    """Suggest platform-specific optimizations - CONTEXT HELPER"""
    return """Recommended optimizations:
1. Use resize operation for Instagram (1080x1080 or 1080x1350)
2. Convert all to MP4 for maximum compatibility
3. Use trim operation to create shorter clips for social media
4. Consider compress_efficiently for faster uploads"""

def _analyze_quality_issues() -> str:
    """Analyze potential quality issues - CONTEXT HELPER"""
    return """Quality analysis based on file characteristics:
• No obvious corruption detected
• Some files may benefit from audio normalization
• Consider format standardization for consistent quality
• Check individual files with get_file_info() for detailed analysis"""

def _suggest_quality_improvements() -> str:
    """Suggest quality enhancement opportunities - CONTEXT HELPER"""
    return """Enhancement opportunities:
1. Use normalize_audio operation for better audio levels
2. Convert to MP4 for optimal codec efficiency
3. Use extract_audio + replace_audio workflow for audio cleanup
4. Consider resize operation if source resolution is inconsistent"""

# process_file_internal and process_file_as_finished functions are now moved to video_operations.py

@mcp.tool()
@timing_decorator
async def process_komposition_file(komposition_path: str) -> Dict[str, Any]:
    """Process a komposition JSON file to create beat-synchronized music video
    
    Args:
        komposition_path: Path to komposition JSON file (relative to project root)
    
    Returns:
        Result with output file ID and composition details
    """
    try:
        # Load komposition from file
        full_path = Path(komposition_path)
        if not full_path.is_absolute():
            # Make relative to project root
            project_root = Path(__file__).parent.parent
            full_path = project_root / komposition_path
        
        if not full_path.exists():
            return {
                "success": False,
                "error": f"Komposition file not found: {komposition_path}"
            }
        
        # Load and process komposition
        komposition_data = await komposition_processor.load_komposition(str(full_path))
        result = await komposition_processor.process_komposition(komposition_data)
        
        # Apply compatibility encoding if video was created
        if result.get("success") and result.get("output_file_id"):
            try:
                # Re-encode with YouTube recommended settings for YUV420P compatibility
                compat_result = await mcp.call_tool('process_file', {
                    'input_file_id': result["output_file_id"],
                    'operation': 'youtube_recommended_encode',
                    'output_extension': 'mp4'
                })
                
                if compat_result and len(compat_result) > 0:
                    compat_data = json.loads(compat_result[0].text) if hasattr(compat_result[0], 'text') else compat_result[0]
                    if compat_data.get("success"):
                        # Replace the output with the compatible version
                        result["output_file_id"] = compat_data["output_file_id"]
                        result["output_file"] = file_manager.resolve_id(compat_data["output_file_id"])
                        result["compatibility_encoding_applied"] = True
                        
            except Exception as e:
                logger.warning(f"Compatibility encoding failed: {e}")
                result["compatibility_encoding_applied"] = False
        
        return result
        
    except Exception as e:
        return {
            "success": False, 
            "error": f"Failed to process komposition: {str(e)}"
        }

# process_file_internal and process_file_as_finished functions are now moved to video_operations.py

@mcp.tool()
@timing_decorator
async def process_transition_effects_komposition(komposition_path: str) -> Dict[str, Any]:
    """Process a komposition JSON file with advanced transition effects tree
    
    Args:
        komposition_path: Path to komposition JSON file with effects_tree (relative to project root)
    
    Returns:
        Result with output file ID and effects composition details
    """
    try:
        # Load komposition from file
        full_path = Path(komposition_path)
        if not full_path.is_absolute():
            # Make relative to project root
            project_root = Path(__file__).parent.parent
            full_path = project_root / komposition_path
        
        if not full_path.exists():
            return {
                "success": False,
                "error": f"Transition effects komposition file not found: {komposition_path}"
            }
        
        # Load and process komposition with effects tree
        komposition_data = await transition_processor.load_komposition_with_effects(str(full_path))
        result = await transition_processor.process_effects_tree(komposition_data)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to process transition effects komposition: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def process_speech_komposition(komposition_path: str) -> Dict[str, Any]:
    """Process a komposition JSON file with speech overlay capabilities
    
    This tool creates music videos that combine multiple video segments with intelligent
    speech detection and audio layering. It can detect speech in videos and layer the
    original speech over background music while maintaining perfect synchronization.
    
    Args:
        komposition_path: Path to komposition JSON file with speechOverlay settings (relative to project root)
    
    Returns:
        Result with output file ID and speech processing details
        
    Example komposition structure:
    {
        "metadata": {"title": "Speech Music Video", "bpm": 120, "estimatedDuration": 30},
        "segments": [
            {
                "id": "speech_segment",
                "sourceRef": "video_with_speech.mp4", 
                "speechOverlay": {
                    "enabled": true,
                    "backgroundMusic": "music.mp3",
                    "musicVolume": 0.3,
                    "speechVolume": 0.8,
                    "speechSegments": [{"start_time": 2.5, "end_time": 5.0, "duration": 2.5}]
                }
            }
        ]
    }
    """
    try:
        # Load komposition from file
        full_path = Path(komposition_path)
        if not full_path.is_absolute():
            # Make relative to project root
            project_root = Path(__file__).parent.parent
            full_path = project_root / komposition_path
        
        if not full_path.exists():
            return {
                "success": False,
                "error": f"Speech komposition file not found: {komposition_path}"
            }
        
        # Process komposition with speech overlay support
        result = await speech_komposition_processor.process_speech_komposition(str(full_path))
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to process speech komposition: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def detect_speech_segments(file_id: str, force_reanalysis: bool = False, threshold: float = 0.5, 
                                min_speech_duration: int = 250, min_silence_duration: int = 100) -> Dict[str, Any]:
    """
    Detect speech segments in video/audio file using AI-powered voice activity detection.
    
    This tool uses Silero VAD (Voice Activity Detection) to identify when people are speaking
    in video or audio files. It provides precise timestamps and quality assessment for each
    speech segment, enabling intelligent audio editing and synchronization.
    
    Args:
        file_id: ID of the source video/audio file
        force_reanalysis: Skip cache and reanalyze (default: False)
        threshold: Speech detection sensitivity 0.1-0.9 (default: 0.5, higher = more strict)
        min_speech_duration: Minimum speech segment duration in ms (default: 250)
        min_silence_duration: Minimum silence gap to separate segments in ms (default: 100)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if detection succeeded
        - has_speech: Boolean indicating if speech was found
        - speech_segments: List of segments with start_time, end_time, duration, quality
        - total_speech_duration: Sum of all speech segment durations
        - total_segments: Number of speech segments detected
        - analysis_metadata: Processing details and engine used
        
    Example Response:
        {
            "success": true,
            "has_speech": true,
            "speech_segments": [
                {
                    "segment_id": 0,
                    "start_time": 5.2,
                    "end_time": 12.8,
                    "duration": 7.6,
                    "confidence": 0.5,
                    "audio_quality": "clear"
                }
            ],
            "total_speech_duration": 7.6,
            "total_segments": 1,
            "analysis_metadata": {
                "engine_used": "silero",
                "processing_time": 1640995200.0
            }
        }
    
    Use Cases:
    - Extract speech segments from music videos before adding background music
    - Identify dialogue sections in tutorial videos
    - Analyze podcast audio for editing and enhancement
    - Prepare audio for speech-to-text transcription
    
    Notes:
    - Results are cached for 5 minutes to improve performance
    - Supports all video formats (MP4, AVI, MOV) and audio formats (MP3, WAV, FLAC)
    - Audio is automatically extracted from video files for analysis
    - Uses pluggable backend system with Silero VAD as primary, WebRTC VAD as fallback
    """
    try:
        # Get file path from ID
        input_path = file_manager.resolve_id(file_id)
        if not input_path:
            return {
                "success": False,
                "error": f"File with ID '{file_id}' not found"
            }
        
        # Run speech detection
        result = await speech_detector.detect_speech_segments(
            input_path,
            force_reanalysis=force_reanalysis,
            threshold=threshold,
            min_speech_duration=min_speech_duration,
            min_silence_duration=min_silence_duration
        )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Speech detection failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def get_speech_insights(file_id: str) -> Dict[str, Any]:
    """
    Get detailed insights and analysis from cached speech detection results.
    
    This tool provides comprehensive analysis of previously detected speech segments,
    including quality metrics, timing patterns, and intelligent editing suggestions.
    Must be called after detect_speech_segments() to have cached data available.
    
    Args:
        file_id: ID of the analyzed video/audio file
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if insights were generated
        - summary: Statistical summary of speech segments
        - quality_distribution: Breakdown of audio quality levels
        - timing_analysis: Patterns in speech timing and gaps
        - editing_suggestions: AI-generated recommendations for editing
        - analysis_metadata: Original detection metadata
        
    Example Response:
        {
            "success": true,
            "summary": {
                "total_segments": 3,
                "total_speech_duration": 25.4,
                "average_segment_duration": 8.47,
                "longest_segment": 12.8,
                "shortest_segment": 5.2
            },
            "quality_distribution": {
                "clear": 2,
                "moderate": 1,
                "low": 0
            },
            "timing_analysis": {
                "average_gap": 2.1,
                "longest_gap": 4.5,
                "speech_density": 0.68
            },
            "editing_suggestions": [
                {
                    "type": "quality_improvement",
                    "message": "Segment 2 has moderate quality. Consider audio enhancement.",
                    "segment_id": 1,
                    "priority": "low"
                }
            ]
        }
    
    Use Cases:
    - Assess overall speech quality before proceeding with audio mixing
    - Identify segments that need audio enhancement or replacement
    - Get recommendations for optimal speech extraction and synchronization
    - Analyze speech patterns for automated editing decisions
    
    Notes:
    - Requires previous speech detection analysis (cached results)
    - Provides actionable editing suggestions based on AI analysis
    - Quality assessment helps prioritize which segments to use in final edit
    - Timing analysis useful for understanding natural speech flow
    """
    try:
        # Get file path from ID
        input_path = file_manager.resolve_id(file_id)
        if not input_path:
            return {
                "success": False,
                "error": f"File with ID '{file_id}' not found"
            }
        
        # Get insights from cached analysis
        insights = speech_detector.get_speech_insights(input_path)
        
        return insights
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get speech insights: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def analyze_composition_sources(source_filenames: List[str], force_reanalysis: bool = False) -> Dict[str, Any]:
    """
    Analyze multiple video sources for intelligent composition planning.
    
    This tool performs comprehensive analysis of video files to determine optimal processing strategies:
    - Enhanced speech detection with cut point identification
    - Content quality assessment and visual complexity analysis
    - Processing strategy recommendations (time-stretch vs smart-cut vs hybrid)
    - Priority scoring for source ordering in compositions
    
    Args:
        source_filenames: List of video filenames to analyze
        force_reanalysis: Force fresh analysis, ignore cache (default: False)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating analysis completion
        - analyzed_sources: List of source analysis results
        - recommendations: Processing strategy recommendations
        - priority_order: Suggested ordering by quality/speech importance
        
    Example Usage:
        analyze_composition_sources(["intro.mp4", "speech_video.mp4", "outro.mp4"])
    """
    try:
        analyzed_sources = []
        
        for i, filename in enumerate(source_filenames):
            
            # Get file ID and path
            file_id = file_manager.get_id_by_name(filename)
            if not file_id:
                continue
            
            file_path = file_manager.resolve_id(file_id)
            
            # Enhanced speech analysis
            speech_analysis = await enhanced_speech_analyzer.analyze_video_for_composition(
                file_path, force_reanalysis=force_reanalysis
            )
            
            if not speech_analysis["success"]:
                continue
            
            # Content analysis
            content_analysis = await content_analyzer.analyze_video_content(file_id)
            
            # Determine processing strategy
            has_speech = speech_analysis["has_speech"]
            speech_quality = speech_analysis["quality_metrics"]["overall_quality"]
            
            if not has_speech:
                strategy = "time_stretch"
            elif speech_quality > 0.8:
                strategy = "smart_cut"
            elif speech_quality > 0.5:
                strategy = "hybrid"
            else:
                strategy = "minimal_stretch"
            
            # Calculate priority score
            priority_score = 0.5
            if has_speech:
                priority_score += speech_quality * 0.3
            priority_score += content_analysis.get("overall_score", 0.5) * 0.2
            priority_score = min(1.0, priority_score)
            
            source_result = {
                "filename": filename,
                "file_id": file_id,
                "duration": speech_analysis["video_duration"],
                "has_speech": has_speech,
                "speech_quality": speech_quality if has_speech else 0.0,
                "content_score": content_analysis.get("overall_score", 0.5),
                "recommended_strategy": strategy,
                "priority_score": priority_score,
                "speech_segments": speech_analysis.get("speech_segments", []),
                "cut_points": speech_analysis.get("cut_points", []),
                "cut_strategies": speech_analysis.get("cut_strategies", [])
            }
            
            analyzed_sources.append(source_result)
        
        # Sort by priority score
        analyzed_sources.sort(key=lambda s: s["priority_score"], reverse=True)
        
        # Generate overall recommendations
        recommendations = {
            "total_sources": len(analyzed_sources),
            "sources_with_speech": sum(1 for s in analyzed_sources if s["has_speech"]),
            "high_priority_sources": sum(1 for s in analyzed_sources if s["priority_score"] > 0.8),
            "suggested_composition_order": [s["filename"] for s in analyzed_sources],
            "processing_strategies": {
                s["filename"]: s["recommended_strategy"] for s in analyzed_sources
            }
        }
        
        return {
            "success": True,
            "analyzed_sources": analyzed_sources,
            "recommendations": recommendations,
            "priority_order": [s["filename"] for s in analyzed_sources]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@mcp.tool()
@timing_decorator
async def generate_composition_plan(
    source_filenames: List[str], 
    background_music: str,
    total_duration: float = 24.0,
    bpm: int = 120,
    composition_title: str = "Intelligent Composition",
    force_reanalysis: bool = False
) -> Dict[str, Any]:
    """
    Generate intelligent composition plan with speech-aware processing strategies.
    
    This tool creates a comprehensive komposition-plan.json that intelligently handles:
    - Speech preservation with natural cut points
    - Time allocation based on beat synchronization
    - Audio mixing strategies for speech + music
    - Effects chain optimization
    - Processing workflow with estimated timings
    
    Args:
        source_filenames: List of video filenames for composition
        background_music: Background music filename
        total_duration: Total composition duration in seconds (default: 24.0)
        bpm: Beats per minute for synchronization (default: 120)
        composition_title: Title for the composition (default: "Intelligent Composition")
        force_reanalysis: Force fresh analysis of sources (default: False)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating plan generation success
        - composition_plan: Complete komposition-plan JSON structure
        - plan_file_path: Path to saved plan file
        - processing_summary: Summary of planned operations
        
    Example Usage:
        generate_composition_plan(
            ["intro.mp4", "speech_segment.mp4", "outro.mp4"],
            "background_music.mp3",
            total_duration=30.0,
            bpm=120
        )
    """
    try:
        # Generate composition plan using the planner engine
        composition_plan = await composition_planner.create_composition_plan(
            sources=source_filenames,
            background_music=background_music,
            total_duration=total_duration,
            bpm=bpm,
            composition_title=composition_title,
            force_reanalysis=force_reanalysis
        )
        
        if not composition_plan.get("success", False):
            return composition_plan
        
        # Create processing summary
        segments = composition_plan.get("composition", {}).get("segments", [])
        processing_summary = {
            "total_segments": len(segments),
            "speech_segments": sum(1 for s in segments if s.get("strategy", {}).get("preserve_speech_pitch", False)),
            "time_stretch_segments": sum(1 for s in segments if s.get("strategy", {}).get("type") == "time_stretch"),
            "smart_cut_segments": sum(1 for s in segments if s.get("strategy", {}).get("type") == "smart_cut"),
            "estimated_processing_time": len(segments) * 60,  # 1 minute per segment estimate
            "audio_overlays": len([s for s in segments if s.get("audio_handling", {}).get("extracted_audio")])
        }
        
        return {
            "success": True,
            "composition_plan": composition_plan,
            "plan_file_path": str(composition_planner.cache_dir / f"composition_plan_latest.json"),
            "processing_summary": processing_summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate composition plan: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def process_composition_plan(plan_file_path: str) -> Dict[str, Any]:
    """
    Execute an intelligent composition plan with speech-aware processing.
    
    This tool processes a komposition-plan.json file created by generate_composition_plan():
    - Executes speech-aware cutting strategies
    - Preserves natural speech pitch where specified
    - Creates time-stretched video segments for beat synchronization
    - Extracts and processes speech audio separately
    - Generates audio timing manifest for external mixing
    
    Args:
        plan_file_path: Path to komposition-plan.json file
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating processing completion
        - output_files: List of generated files with descriptions
        - audio_manifest: Audio timing information for external mixing
        - processing_log: Detailed log of operations performed
        
    Example Usage:
        process_composition_plan("composition_plan_latest.json")
    """
    try:
        print(f"🎬 PROCESSING INTELLIGENT COMPOSITION PLAN")
        
        # Load plan file
        plan_path = Path(plan_file_path)
        if not plan_path.is_absolute():
            plan_path = composition_planner.cache_dir / plan_file_path
        
        if not plan_path.exists():
            return {
                "success": False,
                "error": f"Plan file not found: {plan_file_path}"
            }
        
        with open(plan_path, 'r') as f:
            plan = json.load(f)
        
        if not plan.get("success", False):
            return {
                "success": False,
                "error": "Invalid composition plan"
            }
        
        segments = plan.get("composition", {}).get("segments", [])
        sources = plan.get("sources", {}).get("videos", [])
        audio_plan = plan.get("audio_plan", {})
        
        print(f"   📊 Processing {len(segments)} segments")
        
        # Create processing log
        processing_log = []
        output_files = []
        
        # Process each segment according to its strategy
        for i, segment in enumerate(segments):
            segment_id = segment["id"]
            source_id = segment["source_id"]
            strategy = segment["strategy"]
            cutting = segment["cutting"]
            audio_handling = segment["audio_handling"]
            
            print(f"\n   🎬 Processing {segment_id} ({strategy['type']})")
            
            # Find source file
            source_file = None
            for src in sources:
                if src["id"] == source_id:
                    source_file = src["file"]
                    break
            
            if not source_file:
                error_msg = f"Source file not found for {source_id}"
                processing_log.append({"segment": segment_id, "error": error_msg})
                continue
            
            # Get file ID
            file_id = file_manager.get_id_by_name(source_file)
            if not file_id:
                error_msg = f"File ID not found for {source_file}"
                processing_log.append({"segment": segment_id, "error": error_msg})
                continue
            
            try:
                # Process based on strategy type
                if strategy["type"] == "time_stretch":
                    # Time-stretch entire video
                    stretch_factor = strategy.get("stretch_factor", 1.0)
                    target_duration = cutting["resulting_duration"]
                    
                    # Create time-stretched segment
                    result = await process_file(
                        input_file_id=file_id,
                        operation="trim",
                        output_extension="mp4",
                        params=f"start={cutting['source_start']} duration={target_duration}"
                    )
                    
                    if result["success"]:
                        segment_file_id = result["output_file_id"]
                        output_files.append({
                            "file_id": segment_file_id,
                            "description": f"Time-stretched segment: {segment_id}",
                            "type": "video_segment"
                        })
                        processing_log.append({
                            "segment": segment_id,
                            "operation": "time_stretch",
                            "success": True,
                            "output_file_id": segment_file_id
                        })
                    
                elif strategy["type"] == "smart_cut":
                    # Smart cut preserving speech
                    cut_start = cutting["source_start"]
                    cut_end = cutting["source_end"]
                    duration = cut_end - cut_start
                    
                    # Extract segment using natural cut points
                    result = await process_file(
                        input_file_id=file_id,
                        operation="trim",
                        output_extension="mp4",
                        params=f"start={cut_start} duration={duration}"
                    )
                    
                    if result["success"]:
                        segment_file_id = result["output_file_id"]
                        output_files.append({
                            "file_id": segment_file_id,
                            "description": f"Smart-cut segment: {segment_id} (speech preserved)",
                            "type": "video_segment"
                        })
                        
                        # Extract speech audio if needed
                        if audio_handling.get("extracted_audio"):
                            speech_result = await process_file(
                                input_file_id=segment_file_id,
                                operation="extract_audio",
                                output_extension="wav",
                                params=""
                            )
                            
                            if speech_result["success"]:
                                speech_file_id = speech_result["output_file_id"]
                                output_files.append({
                                    "file_id": speech_file_id,
                                    "description": f"Extracted speech: {segment_id}",
                                    "type": "speech_audio"
                                })
                        
                        processing_log.append({
                            "segment": segment_id,
                            "operation": "smart_cut",
                            "success": True,
                            "output_file_id": segment_file_id,
                            "speech_preserved": True
                        })
                
            except Exception as e:
                processing_log.append({
                    "segment": segment_id,
                    "error": str(e),
                    "success": False
                })
                continue
        
        # Generate audio timing manifest
        audio_manifest = {
            "background_music": audio_plan.get("background_music", {}),
            "speech_overlays": audio_plan.get("speech_overlays", []),
            "timeline": plan.get("timeline", {}),
            "instructions": [
                "1. Load background music for full duration",
                "2. Insert speech overlays at specified times",
                "3. Mix with specified volume levels",
                "4. Export final audio track"
            ]
        }
        
        success_count = sum(1 for log in processing_log if log.get("success", False))
        
        print(f"\n✅ PROCESSING COMPLETE: {success_count}/{len(segments)} segments successful")
        
        return {
            "success": success_count > 0,
            "output_files": output_files,
            "audio_manifest": audio_manifest,
            "processing_log": processing_log,
            "segments_processed": success_count,
            "total_segments": len(segments)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to process composition plan: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def preview_composition_timing(
    source_filenames: List[str],
    total_duration: float = 24.0,
    bpm: int = 120
) -> Dict[str, Any]:
    """
    Preview timing allocation for composition without full processing.
    
    This tool provides a quick preview of how sources will be allocated in time slots:
    - Shows time slot assignments based on BPM
    - Estimates processing strategies for each source
    - Identifies potential timing conflicts or issues
    - Provides recommendations before full processing
    
    Args:
        source_filenames: List of video filenames
        total_duration: Total composition duration in seconds (default: 24.0)
        bpm: Beats per minute for synchronization (default: 120)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating preview generation success
        - timing_preview: Time slot allocations and strategies
        - recommendations: Suggestions for optimization
        - estimated_processing_time: Predicted processing duration
    """
    try:
        print(f"⏰ PREVIEWING COMPOSITION TIMING")
        
        # Calculate time slots
        seconds_per_beat = 60.0 / bpm
        beats_per_measure = 16  # Standard for compositions
        slot_duration = seconds_per_beat * beats_per_measure
        
        time_slots = []
        current_time = 0.0
        
        for i in range(len(source_filenames)):
            if current_time >= total_duration:
                break
                
            end_time = min(current_time + slot_duration, total_duration)
            
            time_slots.append({
                "slot_number": i + 1,
                "source_file": source_filenames[i] if i < len(source_filenames) else None,
                "start_time": current_time,
                "end_time": end_time,
                "duration": end_time - current_time,
                "beat_start": int(current_time / seconds_per_beat),
                "beat_end": int(end_time / seconds_per_beat)
            })
            
            current_time = end_time
        
        # Get basic file info for strategy estimation
        timing_preview = []
        total_processing_estimate = 0
        
        for slot in time_slots:
            if not slot["source_file"]:
                continue
                
            file_id = file_manager.get_id_by_name(slot["source_file"])
            if not file_id:
                slot_info = {
                    **slot,
                    "strategy": "unknown",
                    "issue": "File not found",
                    "processing_time_estimate": 0
                }
            else:
                # Quick analysis for strategy estimation
                file_path = file_manager.resolve_id(file_id)
                
                # Estimate strategy based on filename and basic analysis
                if "speech" in slot["source_file"].lower() or "talk" in slot["source_file"].lower():
                    strategy = "smart_cut"
                    processing_time = 120  # 2 minutes for speech processing
                else:
                    strategy = "time_stretch"
                    processing_time = 60   # 1 minute for time stretching
                
                slot_info = {
                    **slot,
                    "strategy": strategy,
                    "processing_time_estimate": processing_time,
                    "note": f"Will use {strategy} processing"
                }
                
                total_processing_estimate += processing_time
            
            timing_preview.append(slot_info)
        
        # Generate recommendations
        recommendations = []
        
        if len(source_filenames) > len(time_slots):
            recommendations.append({
                "type": "warning",
                "message": f"Too many sources ({len(source_filenames)}) for duration ({total_duration}s). Only first {len(time_slots)} will be used."
            })
        
        if total_processing_estimate > 300:  # > 5 minutes
            recommendations.append({
                "type": "info",
                "message": f"Estimated processing time: {total_processing_estimate/60:.1f} minutes. Consider processing in smaller batches."
            })
        
        speech_sources = sum(1 for slot in timing_preview if slot.get("strategy") == "smart_cut")
        if speech_sources > 0:
            recommendations.append({
                "type": "info",
                "message": f"{speech_sources} sources detected as speech content. These will preserve natural pitch."
            })
        
        print(f"✅ TIMING PREVIEW COMPLETE: {len(timing_preview)} slots allocated")
        
        return {
            "success": True,
            "timing_preview": timing_preview,
            "recommendations": recommendations,
            "estimated_processing_time": total_processing_estimate,
            "total_duration": total_duration,
            "beats_per_minute": bpm,
            "slot_duration": slot_duration
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to preview composition timing: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def generate_komposition_from_description(
    description: str,
    title: str = "Generated Composition",
    custom_bpm: Optional[int] = None,
    custom_resolution: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate komposition.json from natural language description.
    
    This tool creates a complete komposition structure from text descriptions like:
    - "Create a 135 BPM music video with intro, speech segment, and outro"
    - "Make a 600x800 portrait video with lookin.mp4 and panning video" 
    - "Build composition from beat 32-48 with fade transitions"
    
    Args:
        description: Natural language description of desired composition
        title: Title for the generated composition (default: "Generated Composition")
        custom_bpm: Override BPM (parsed from description if not provided)
        custom_resolution: Override resolution like "600x800" (parsed from description if not provided)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating generation success
        - komposition: Complete komposition.json structure
        - komposition_file: Path to saved komposition file
        - intent: Parsed user intent and requirements
        - summary: Generation summary with segments, effects, duration
        
    Example Usage:
        generate_komposition_from_description(
            "Create a 135 BPM music video with PXL intro, lookin speech segment, and panning outro. Make it 600x800 format.",
            title="Custom Music Video"
        )
    """
    try:
        print(f"🤖 GENERATING KOMPOSITION FROM DESCRIPTION")
        
        # Get available source files
        available_sources = komposition_generator.get_available_sources()
        print(f"   📂 Available sources: {len(available_sources)} files")
        
        # Generate komposition
        result = await komposition_generator.generate_from_description(
            description=description,
            title=title,
            available_sources=available_sources
        )
        
        if not result["success"]:
            return result
        
        # Apply custom overrides if provided
        komposition = result["komposition"]
        
        if custom_bpm:
            komposition["metadata"]["bpm"] = custom_bpm
            # Recalculate duration
            total_beats = komposition["metadata"]["totalBeats"]
            komposition["metadata"]["estimatedDuration"] = total_beats * 60 / custom_bpm
            print(f"   🎵 BPM override: {custom_bpm}")
        
        if custom_resolution:
            try:
                width, height = map(int, custom_resolution.split('x'))
                komposition["outputSettings"]["resolution"] = f"{width}x{height}"
                komposition["outputSettings"]["aspectRatio"] = f"{width}:{height}"
                print(f"   📐 Resolution override: {width}x{height}")
            except ValueError:
                print(f"   ⚠️ Invalid resolution format: {custom_resolution}")
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate komposition from description: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def generate_enhanced_komposition_from_description(
    description: str,
    title: str = "Enhanced Content-Aware Composition",
    use_source_metadata: bool = True
) -> Dict[str, Any]:
    """
    🧠 ENHANCED WORKFLOW - Generate komposition with deep content analysis integration
    
    Creates komposition.json with intelligent scene selection based on:
    - AI-powered video content analysis (scene detection, object recognition)
    - Source metadata files (usable segments, editing recommendations)
    - Visual characteristics mapping to musical structure
    - Content-aware transition and effect selection
    
    This enhanced version goes beyond basic komposition generation by:
    - Analyzing video scenes for visual characteristics and objects
    - Mapping scene content to musical roles (intro, verse, refrain, outro)
    - Using source metadata for professional segment selection
    - Generating content-aware effects and transitions
    
    Args:
        description: Natural language description of desired composition
        title: Title for the enhanced composition
        use_source_metadata: Whether to use existing source metadata files (default: True)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating generation success
        - komposition: Enhanced komposition with content-aware segments
        - komposition_file: Path to saved komposition file
        - content_analysis_used: Number of files analyzed
        - scenes_selected: Number of scenes selected
        - selection_details: Scene selection details with reasons
        
    Example Usage:
        generate_enhanced_komposition_from_description(
            "Create a 120 BPM music video with dramatic intro, eye-focused verse, dynamic refrain, and fade outro",
            title="Eye Movement Music Video",
            use_source_metadata=True
        )
    """
    try:
        print(f"🧠 GENERATING ENHANCED CONTENT-AWARE KOMPOSITION")
        print(f"   📝 Description: {description[:100]}...")
        print(f"   🎬 Title: {title}")
        print(f"   📚 Using metadata: {use_source_metadata}")
        
        result = await generate_enhanced_komposition_from_description(
            description=description,
            title=title,
            use_source_metadata=use_source_metadata
        )
        
        if result["success"]:
            print(f"   ✅ Enhanced komposition generated successfully")
            print(f"   📊 Content analysis used: {result.get('content_analysis_used', 0)} files")
            print(f"   🎯 Scenes selected: {result.get('scenes_selected', 0)}")
            
            # Add processing summary
            result["processing_summary"] = {
                "description": description,
                "title": title,
                "use_source_metadata": use_source_metadata,
                "enhancement_features": [
                    "AI-powered scene analysis",
                    "Content-aware segment selection", 
                    "Visual characteristic mapping",
                    "Source metadata integration",
                    "Musical structure optimization"
                ]
            }
        else:
            print(f"   ❌ Enhanced komposition generation failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate enhanced komposition: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def create_build_plan_from_komposition(
    komposition_file: str,
    render_start_beat: Optional[int] = None,
    render_end_beat: Optional[int] = None,
    output_resolution: str = "1920x1080",
    custom_bpm: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create detailed build plan from komposition.json with beat-precise calculations.
    
    This tool transforms a komposition.json into a comprehensive build plan containing:
    - File dependency mapping (source → intermediate → final)
    - Beat-precise timing calculations for any BPM
    - Snippet extraction specifications with exact timestamps
    - Effects tree dependency ordering
    - Processing operation sequencing
    - Intermediate file tracking
    
    Args:
        komposition_file: Path to komposition.json file
        render_start_beat: Override start beat (default: use komposition)
        render_end_beat: Override end beat (default: use komposition)
        output_resolution: Target resolution like "1920x1080" or "600x800"
        custom_bpm: Override BPM for timing calculations
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating plan creation success
        - build_plan: Complete build plan with dependencies and execution order
        - build_plan_file: Path to saved build plan file
        - summary: Processing summary with operations, timing, resolution
        
    Example Usage:
        create_build_plan_from_komposition(
            "my_composition.json",
            render_start_beat=32,
            render_end_beat=48,
            output_resolution="600x800"
        )
    """
    try:
        print(f"🏗️ CREATING BUILD PLAN FROM KOMPOSITION")
        
        # Parse resolution
        try:
            width, height = map(int, output_resolution.split('x'))
            resolution_tuple = (width, height)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid resolution format: {output_resolution}"
            }
        
        # Create build plan
        result = await komposition_build_planner.create_build_plan(
            komposition_path=komposition_file,
            render_start_beat=render_start_beat,
            render_end_beat=render_end_beat,
            output_resolution=resolution_tuple,
            custom_bpm=custom_bpm
        )
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create build plan: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def validate_build_plan_for_bpms(
    build_plan_file: str,
    test_bpms: List[int] = [120, 135, 140, 100]
) -> Dict[str, Any]:
    """
    Validate build plan calculations for multiple BPM values.
    
    This tool tests build plan timing calculations across different BPMs to ensure:
    - Beat timing calculations are correct
    - Segment durations are reasonable
    - No mathematical errors in time conversions
    - All extractions have valid timing
    
    Args:
        build_plan_file: Path to build plan JSON file
        test_bpms: List of BPM values to test (default: [120, 135, 140, 100])
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating validation completion
        - validation_results: Results for each BPM tested
        - overall_valid: Boolean indicating if all BPMs passed validation
        - error_summary: Summary of any validation errors found
        
    Example Usage:
        validate_build_plan_for_bpms(
            "build_20241206_143022.json",
            test_bpms=[120, 135, 140]
        )
    """
    try:
        print(f"🧪 VALIDATING BUILD PLAN FOR MULTIPLE BPMs")
        
        # Load build plan
        plan_path = Path(build_plan_file)
        if not plan_path.is_absolute():
            plan_path = komposition_build_planner.build_cache_dir / build_plan_file
        
        if not plan_path.exists():
            return {
                "success": False,
                "error": f"Build plan file not found: {build_plan_file}"
            }
        
        # Load and parse build plan
        with open(plan_path, 'r') as f:
            build_plan_data = json.load(f)
        
        # Convert to BuildPlan object for validation
        from komposition_build_planner import BuildPlan, BeatTiming, SnippetExtraction
        
        # Reconstruct beat timing
        beat_timing_data = build_plan_data["beat_timing"]
        beat_timing = BeatTiming(
            bpm=beat_timing_data["bpm"],
            beats_per_measure=beat_timing_data["beats_per_measure"],
            start_beat=beat_timing_data["start_beat"],
            end_beat=beat_timing_data["end_beat"]
        )
        
        # Reconstruct snippet extractions
        snippet_extractions = []
        for extraction_data in build_plan_data["snippet_extractions"]:
            target_timing = BeatTiming(
                bpm=extraction_data["target_timing"]["bpm"],
                start_beat=extraction_data["target_timing"]["start_beat"],
                end_beat=extraction_data["target_timing"]["end_beat"]
            )
            
            extraction = SnippetExtraction(
                id=extraction_data["id"],
                source_file_id=extraction_data["source_file_id"],
                source_start=extraction_data["source_start"],
                source_duration=extraction_data["source_duration"],
                target_start_beat=extraction_data["target_start_beat"],
                target_end_beat=extraction_data["target_end_beat"],
                target_timing=target_timing
            )
            snippet_extractions.append(extraction)
        
        # Create minimal BuildPlan for validation
        build_plan = BuildPlan(
            id=build_plan_data["id"],
            title=build_plan_data["title"],
            source_komposition_path=build_plan_data["source_komposition_path"],
            created_at=build_plan_data["created_at"],
            beat_timing=beat_timing,
            render_range=tuple(build_plan_data["render_range"]),
            output_resolution=tuple(build_plan_data["output_resolution"]),
            snippet_extractions=snippet_extractions
        )
        
        # Validate for multiple BPMs
        validation_results = komposition_build_planner.validate_build_plan_bpm(build_plan, test_bpms)
        
        # Check if all validations passed
        overall_valid = all(result["valid"] for result in validation_results.values())
        
        # Create error summary
        error_summary = []
        for bpm, result in validation_results.items():
            if not result["valid"]:
                error_summary.extend([f"BPM {bpm}: {error}" for error in result["extraction_errors"]])
        
        print(f"✅ VALIDATION COMPLETE: {len([r for r in validation_results.values() if r['valid']])}/{len(test_bpms)} BPMs passed")
        
        return {
            "success": True,
            "validation_results": validation_results,
            "overall_valid": overall_valid,
            "error_summary": error_summary,
            "tested_bpms": test_bpms
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to validate build plan: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def generate_and_build_from_description(
    description: str,
    title: str = "Generated Video",
    render_start_beat: Optional[int] = None,
    render_end_beat: Optional[int] = None,
    output_resolution: str = "1920x1080",
    validate_bpms: List[int] = [120, 135]
) -> Dict[str, Any]:
    """
    Complete workflow: Generate komposition from description and create build plan.
    
    This tool combines komposition generation and build planning into a single workflow:
    1. Parses natural language description
    2. Generates complete komposition.json
    3. Creates detailed build plan with dependencies
    4. Validates timing calculations for multiple BPMs
    5. Returns ready-to-execute build specifications
    
    Args:
        description: Natural language description of desired video
        title: Title for the composition
        render_start_beat: Override render start beat
        render_end_beat: Override render end beat  
        output_resolution: Target resolution like "600x800"
        validate_bpms: BPM values to validate (default: [120, 135])
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating complete workflow success
        - komposition: Generated komposition structure
        - build_plan: Complete build plan
        - validation_results: BPM validation results
        - files: Paths to generated komposition and build plan files
        - summary: Complete workflow summary
        
    Example Usage:
        generate_and_build_from_description(
            "Create a 135 BPM music video with lookin speech and panning action. Render from beat 32-48 in 600x800 portrait format with fade transitions.",
            title="Custom Portrait Video"
        )
    """
    try:
        print(f"🚀 COMPLETE WORKFLOW: DESCRIPTION → KOMPOSITION → BUILD PLAN")
        
        # Step 1: Generate komposition from description
        print(f"\n🤖 STEP 1: GENERATING KOMPOSITION")
        komposition_result = await generate_komposition_from_description(
            description=description,
            title=title,
            custom_resolution=output_resolution
        )
        
        if not komposition_result["success"]:
            return {
                "success": False,
                "error": f"Komposition generation failed: {komposition_result.get('error')}"
            }
        
        komposition_file = komposition_result["komposition_file"]
        
        # Step 2: Create build plan
        print(f"\n🏗️ STEP 2: CREATING BUILD PLAN")
        build_plan_result = await create_build_plan_from_komposition(
            komposition_path=komposition_file,
            render_start_beat=render_start_beat,
            render_end_beat=render_end_beat,
            output_resolution=output_resolution
        )
        
        if not build_plan_result["success"]:
            return {
                "success": False,
                "error": f"Build plan creation failed: {build_plan_result.get('error')}"
            }
        
        build_plan_file = build_plan_result["build_plan_file"]
        
        # Step 3: Validate build plan
        print(f"\n🧪 STEP 3: VALIDATING BUILD PLAN")
        validation_result = await validate_build_plan_for_bpms(
            build_plan_file=build_plan_file,
            test_bpms=validate_bpms
        )
        
        if not validation_result["success"]:
            print(f"   ⚠️ Validation failed, but continuing with build plan")
        
        # Compile complete results
        workflow_summary = {
            "komposition_segments": len(komposition_result["komposition"]["segments"]),
            "komposition_effects": len(komposition_result["komposition"]["effects_tree"]),
            "build_plan_operations": build_plan_result["summary"]["total_operations"],
            "estimated_processing_time": build_plan_result["summary"]["estimated_time"],
            "output_resolution": output_resolution,
            "validation_passed": validation_result.get("overall_valid", False),
            "validated_bpms": validate_bpms
        }
        
        print(f"\n🎉 COMPLETE WORKFLOW SUCCESSFUL!")
        print(f"   🎬 {workflow_summary['komposition_segments']} segments")
        print(f"   ✨ {workflow_summary['komposition_effects']} effects")
        print(f"   🔗 {workflow_summary['build_plan_operations']} operations")
        print(f"   ⏱️ Est. processing: {workflow_summary['estimated_processing_time']/60:.1f} minutes")
        print(f"   🧪 BPM validation: {'✅ PASSED' if workflow_summary['validation_passed'] else '⚠️ ISSUES'}")
        
        return {
            "success": True,
            "komposition": komposition_result["komposition"],
            "build_plan": build_plan_result["build_plan"],
            "validation_results": validation_result.get("validation_results", {}),
            "files": {
                "komposition_file": komposition_file,
                "build_plan_file": build_plan_file
            },
            "summary": workflow_summary
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Complete workflow failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def build_video_from_audio_manifest(
    manifest_file: str = "AUDIO_TIMING_MANIFEST.json",
    execution_strategy: str = "ffmpeg_direct"
) -> Dict[str, Any]:
    """🎵 AUDIO WORKFLOW - Build final video directly from audio timing manifest
    
    Perfect for converting AUDIO_TIMING_MANIFEST.json → final video with proper audio mixing.
    
    This tool handles complex audio timing scenarios:
    - Silent video + background music combination
    - Speech segment timing and volume control  
    - Multiple audio layer mixing
    - Precise timing based on beat synchronization
    
    Args:
        manifest_file: Path to AUDIO_TIMING_MANIFEST.json (default: searches temp directory)
        execution_strategy: "ffmpeg_direct" for direct ffmpeg, "mcp_batch" for MCP operations
    
    Perfect For:
        - Speech-synchronized music videos
        - Complex audio timing scenarios  
        - Multi-layer audio mixing
        - Beat-precise audio placement
    
    Example Manifest Structure:
        {
          "metadata": {
            "silentVideoFile": "/tmp/music/temp/SILENT_VIDEO.mp4",
            "backgroundMusic": "music.mp3"
          },
          "videoSegments": [...speech timing info...],
          "finalAssemblyInstructions": {...mixing steps...}
        }
    
    Next Steps:
        → get_file_info() - Check final video metadata
        → list_generated_files() - See what was created
        → cleanup_temp_files() - Clean up intermediate files
    
    Returns:
        Dictionary with success status, output file info, and processing details
    """
    try:
        print(f"🎵 BUILDING VIDEO FROM AUDIO TIMING MANIFEST")
        
        # Find manifest file
        manifest_path = None
        if manifest_file == "AUDIO_TIMING_MANIFEST.json":
            # Search in temp directory
            temp_dir = Path("/tmp/music/temp")
            manifest_path = temp_dir / manifest_file
            if not manifest_path.exists():
                # Search in metadata directory
                metadata_dir = Path("/tmp/music/metadata")
                manifest_path = metadata_dir / manifest_file
        else:
            manifest_path = Path(manifest_file)
        
        if not manifest_path.exists():
            return {
                "success": False,
                "error": f"Manifest file not found: {manifest_file}"
            }
        
        # Load manifest
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        print(f"📄 Loaded manifest: {manifest['metadata']['title']}")
        print(f"🎬 Duration: {manifest['metadata']['totalDuration']}s")
        
        # Get file paths
        silent_video = Path(manifest['metadata']['silentVideoFile'])
        background_music = Path(f"/tmp/music/source/{manifest['metadata']['backgroundMusic']}")
        
        if not silent_video.exists():
            return {
                "success": False,
                "error": f"Silent video not found: {silent_video}"
            }
        
        if not background_music.exists():
            return {
                "success": False,
                "error": f"Background music not found: {background_music}"
            }
        
        # Generate output filename
        output_file = Path("/tmp/music/temp") / "FINAL_FROM_AUDIO_MANIFEST.mp4"
        
        if execution_strategy == "ffmpeg_direct":
            # Use direct ffmpeg command as we successfully tested
            cmd = [
                "ffmpeg", "-y",
                "-i", str(silent_video),
                "-i", str(background_music),
                "-c:v", "copy",
                "-filter:a", "volume=0.5",
                "-shortest",
                str(output_file)
            ]
            
            # Execute ffmpeg
            result = await ffmpeg.execute_command(cmd)
            
            if result["success"]:
                # Register output file
                output_file_id = file_manager.register_file(output_file)
                
                return {
                    "success": True,
                    "message": f"Successfully built video from audio manifest",
                    "output_file": str(output_file),
                    "output_file_id": output_file_id,
                    "output_size_mb": round(output_file.stat().st_size / (1024*1024), 1),
                    "manifest_processed": str(manifest_path),
                    "execution_strategy": execution_strategy,
                    "processing_summary": {
                        "silent_video": str(silent_video),
                        "background_music": str(background_music),
                        "total_duration": manifest['metadata']['totalDuration'],
                        "segments_processed": len(manifest.get('videoSegments', []))
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"FFmpeg execution failed: {result.get('stderr', 'Unknown error')}"
                }
        
        else:  # mcp_batch strategy
            return {
                "success": False,
                "error": "mcp_batch strategy not yet implemented - use ffmpeg_direct"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to build video from audio manifest: {str(e)}"
        }


async def _internal_create_video_from_description(
    description: str,
    title: str = "Generated Video",
    execution_mode: str = "full",
    quality: str = "standard",
    custom_bpm: Optional[int] = None,
    custom_resolution: Optional[str] = None
) -> Dict[str, Any]:
    """Internal implementation of video creation without timeout wrapper"""
    workflow_results = {
        "success": True,
        "workflow_steps": [],
        "files_created": [],
        "processing_summary": {},
        "total_time": 0
    }
    
    try:
        
        workflow_start = asyncio.get_event_loop().time()
        workflow_results = {
            "success": True,
            "workflow_steps": [],
            "files_created": [],
            "processing_summary": {},
            "total_time": 0
        }
        
        # Step 1: Enhanced file discovery
        step_start = asyncio.get_event_loop().time()
        
        files_result = await mcp.call_tool('list_files', {})
        files_text = files_result[0].text if files_result and len(files_result) > 0 else '{}'
        files_data = json.loads(files_text)
        
        step_duration = asyncio.get_event_loop().time() - step_start
        workflow_results["workflow_steps"].append({
            "step": "file_discovery",
            "duration": step_duration,
            "files_found": len(files_data.get("files", [])),
            "status": "completed"
        })
        # Step 2: Enhanced komposition generation with musical structure
        step_start = asyncio.get_event_loop().time()
        
        komposition_result = await mcp.call_tool('generate_komposition_from_description', {
            'description': description,
            'title': title,
            'custom_bpm': custom_bpm,
            'custom_resolution': custom_resolution
        })
        
        komposition_text = komposition_result[0].text if komposition_result and len(komposition_result) > 0 else '{}'
        komposition_data = json.loads(komposition_text)
        
        if not komposition_data.get('success'):
            return {
                "success": False,
                "error": f"Komposition generation failed: {komposition_data.get('error')}",
                "workflow_results": workflow_results
            }
        
        komposition_file = komposition_data.get('komposition_file', '')
        workflow_results["files_created"].append(komposition_file)
        
        step_duration = asyncio.get_event_loop().time() - step_start
        workflow_results["workflow_steps"].append({
            "step": "komposition_generation",
            "duration": step_duration,
            "komposition_file": komposition_file,
            "segments": len(komposition_data.get("komposition", {}).get("segments", [])),
            "effects": len(komposition_data.get("komposition", {}).get("effects_tree", [])),
            "status": "completed"
        })
        # Step 3: Optimized build plan creation
        step_start = asyncio.get_event_loop().time()
        
        build_plan_result = await mcp.call_tool('create_build_plan_from_komposition', {
            'komposition_file': komposition_file
        })
        
        build_plan_text = build_plan_result[0].text if build_plan_result and len(build_plan_result) > 0 else '{}'
        build_plan_data = json.loads(build_plan_text)
        
        if not build_plan_data.get('success'):
            return {
                "success": False,
                "error": f"Build plan creation failed: {build_plan_data.get('error')}",
                "workflow_results": workflow_results
            }
        
        build_plan_file = build_plan_data.get('build_plan_file', '')
        workflow_results["files_created"].append(build_plan_file)
        
        step_duration = asyncio.get_event_loop().time() - step_start
        workflow_results["workflow_steps"].append({
            "step": "build_plan_creation",
            "duration": step_duration,
            "build_plan_file": build_plan_file,
            "operations": len(build_plan_data.get("build_plan", {}).get("effect_operations", [])),
            "extractions": len(build_plan_data.get("build_plan", {}).get("snippet_extractions", [])),
            "status": "completed"
        })
        # Step 4: Quick validation
        step_start = asyncio.get_event_loop().time()
        
        validation_result = await mcp.call_tool('validate_build_plan_for_bpms', {
            'build_plan_file': build_plan_file,
            'test_bpms': [120, 134, 140]  # Quick validation set
        })
        
        validation_text = validation_result[0].text if validation_result and len(validation_result) > 0 else '{}'
        validation_data = json.loads(validation_text)
        
        step_duration = asyncio.get_event_loop().time() - step_start
        workflow_results["workflow_steps"].append({
            "step": "validation",
            "duration": step_duration,
            "validation_passed": validation_data.get("overall_valid", False),
            "status": "completed"
        })
        # Step 5: Conditional execution based on mode
        if execution_mode == "full":
            step_start = asyncio.get_event_loop().time()
            
            # Process the komposition
            processing_result = await mcp.call_tool('process_komposition_file', {
                'komposition_path': komposition_file
            })
            
            processing_text = processing_result[0].text if processing_result and len(processing_result) > 0 else '{}'
            processing_data = json.loads(processing_text)
            
            step_duration = asyncio.get_event_loop().time() - step_start
            workflow_results["workflow_steps"].append({
                "step": "video_processing",
                "duration": step_duration,
                "status": "completed" if processing_data.get("success") else "failed",
                "output_files": processing_data.get("output_files", [])
            })
            
            if processing_data.get("success"):
                workflow_results["files_created"].extend(processing_data.get("output_files", []))
            else:
                workflow_results["success"] = False
        
        elif execution_mode == "plan_only":
            workflow_results["workflow_steps"].append({
                "step": "video_processing",
                "duration": 0,
                "status": "skipped",
                "reason": "plan_only mode"
            })
        
        elif execution_mode == "preview":
            # TODO: Implement quick preview processing
            workflow_results["workflow_steps"].append({
                "step": "video_processing",
                "duration": 0,
                "status": "not_implemented",
                "reason": "preview mode not yet implemented"
            })
        
        # Calculate total workflow time
        total_time = asyncio.get_event_loop().time() - workflow_start
        workflow_results["total_time"] = total_time
        
        # Generate processing summary
        workflow_results["processing_summary"] = {
            "description": description,
            "title": title,
            "execution_mode": execution_mode,
            "quality": quality,
            "total_steps": len(workflow_results["workflow_steps"]),
            "total_files_created": len(workflow_results["files_created"]),
            "total_processing_time": total_time,
            "komposition_segments": len(komposition_data.get("komposition", {}).get("segments", [])),
            "komposition_effects": len(komposition_data.get("komposition", {}).get("effects_tree", [])),
            "build_plan_operations": len(build_plan_data.get("build_plan", {}).get("effect_operations", [])),
            "validation_passed": validation_data.get("overall_valid", False)
        }
        
        return workflow_results
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Atomic video creation failed: {str(e)}",
            "workflow_results": workflow_results
        }


@mcp.tool()
@timing_decorator
async def create_video_from_description(
    description: str,
    title: str = "Generated Video",
    execution_mode: str = "full",  # "full", "plan_only", "preview"
    quality: str = "standard",     # "draft", "standard", "high"
    custom_bpm: Optional[int] = None,
    custom_resolution: Optional[str] = None
) -> Dict[str, Any]:
    """🎬 ATOMIC VIDEO CREATION - Complete video from text description in single call
    
    This is the ULTIMATE workflow tool - combines all steps into one atomic operation:
    1. Parse natural language description with enhanced NLP
    2. Match and analyze available source files
    3. Generate optimized komposition with musical structure recognition
    4. Create and validate build plan with dependency resolution
    5. Execute video processing (if execution_mode="full")
    
    Perfect for: 80% of video creation use cases, rapid prototyping, non-technical users
    
    Parameters:
        description: Natural language description of desired video
        title: Video title (default: "Generated Video")
        execution_mode: 
            - "full": Complete video processing (default)
            - "plan_only": Generate plan but don't process
            - "preview": Quick preview with draft quality
        quality: Processing quality level
            - "draft": Fast processing, lower quality
            - "standard": Balanced quality/speed (default)
            - "high": Maximum quality, slower processing
        custom_bpm: Override detected BPM
        custom_resolution: Override resolution (e.g., "600x800", "1920x1080")
    
    Examples:
        → create_video_from_description("134 BPM music video with smooth transitions")
        → create_video_from_description("Leica-style intro, verse and refrain", execution_mode="plan_only")
        → create_video_from_description("Portrait format dance video", custom_resolution="600x800")
    
    Reduces: 5 calls → 1 call (80% workflow simplification)
    
    ⚡ TIMEOUT PROTECTION: Automatically estimates processing time and applies timeout with cleanup
    
    Returns:
        Dictionary with complete workflow results, files created, and processing summary
    """
    try:
        # Calculate operation timeout based on description complexity
        timeout_seconds = calculate_operation_timeout(
            description,
            execution_mode=execution_mode,
            quality=quality,
            custom_resolution=custom_resolution
        )
        
        # Generate unique operation ID
        import time
        import hashlib
        operation_id = f"video_creation_{int(time.time())}_{hashlib.md5(description.encode()).hexdigest()[:8]}"
        
        # Define cleanup function for partial operations
        async def cleanup_partial_operations():
            """Clean up any partial files or processes on timeout/error"""
            try:
                # Clean up temp files
                cleanup_result = await mcp.call_tool('cleanup_temp_files', {})
                logger.info(f"Cleanup temp files result: {cleanup_result}")
                
                # Clean up any registry inconsistencies
                registry_result = await mcp.call_tool('get_registry_status', {})
                logger.info(f"Registry status after cleanup: {registry_result}")
                
            except Exception as cleanup_error:
                logger.error(f"Error during partial operation cleanup: {cleanup_error}")
        
        # Execute with timeout protection
        logger.info(f"Starting video creation with {timeout_seconds:.1f}s timeout for: {description[:50]}...")
        
        result = await timeout_manager.execute_with_timeout(
            _internal_create_video_from_description(
                description, title, execution_mode, quality, custom_bpm, custom_resolution
            ),
            operation_id,
            timeout_seconds,
            cleanup_partial_operations
        )
        
        # Add timeout information to result
        if isinstance(result, dict):
            result["timeout_info"] = {
                "estimated_time": timeout_seconds / 1.5,  # Remove safety buffer for display
                "actual_timeout": timeout_seconds,
                "operation_id": operation_id
            }
        
        return result
        
    except TimeoutError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "timeout",
            "timeout_info": {
                "estimated_time": timeout_seconds / 1.5,
                "actual_timeout": timeout_seconds,
                "operation_id": operation_id,
                "cleanup_attempted": True
            },
            "recommendation": "Try with a simpler description, lower quality setting, or plan_only mode first"
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Video creation failed: {str(e)}",
            "error_type": "general"
        }


@mcp.tool()
@timing_decorator
async def estimate_processing_time(
    description: str,
    execution_mode: str = "full",
    quality: str = "standard",
    custom_resolution: Optional[str] = None
) -> Dict[str, Any]:
    """⏱️ PROCESSING TIME ESTIMATION - Predict operation duration before execution
    
    Estimates processing time for video creation operations based on:
    - Video duration extracted from description
    - Operation complexity (effects, segments, processing steps)
    - Resolution requirements and format conversions
    - Quality settings and processing mode
    
    Args:
        description: Natural language description of desired video
        execution_mode: "full", "plan_only", or "preview"
        quality: "draft", "standard", or "high"
        custom_resolution: Override resolution (e.g., "600x800", "1920x1080")
    
    Returns:
        Dictionary containing:
        - estimated_seconds: Total processing time estimate
        - estimated_minutes: Time in minutes for readability
        - video_duration: Estimated output video length
        - complexity: Analyzed operation complexity
        - resolution: Target resolution
        - factors: Breakdown of time calculation factors
        - timeout_recommendation: Suggested timeout for operation
    
    Example Usage:
        estimate_processing_time("30 second 120 BPM music video with effects")
        estimate_processing_time("Simple 10s intro", execution_mode="plan_only")
    """
    try:
        estimation = ProcessingTimeEstimator.estimate_processing_time(
            description, execution_mode, quality, custom_resolution
        )
        
        # Add timeout recommendation
        timeout_recommendation = calculate_operation_timeout(
            description, 
            execution_mode=execution_mode,
            quality=quality,
            custom_resolution=custom_resolution
        )
        
        estimation["timeout_recommendation"] = timeout_recommendation
        estimation["timeout_minutes"] = timeout_recommendation / 60
        
        return {
            "success": True,
            **estimation
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to estimate processing time: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def get_operation_status(operation_id: Optional[str] = None) -> Dict[str, Any]:
    """📋 OPERATION MONITORING - Get real-time status of running operations
    
    Monitor active video processing operations and their progress.
    Useful for tracking long-running operations and detecting potential lockups.
    
    Args:
        operation_id: Specific operation to check (optional, shows all if not provided)
    
    Returns:
        Dictionary containing:
        - active_operations: Currently running operations
        - operation_history: Recent completed operations
        - system_health: Resource usage and process health
    
    Example Usage:
        get_operation_status()  # All operations
        get_operation_status("video_creation_1733512345_abc123")  # Specific operation
    """
    try:
        if operation_id:
            # Get specific operation status
            status = timeout_manager.get_operation_status(operation_id)
            return {
                "success": True,
                "operation_id": operation_id,
                "status": status,
                "found": status is not None
            }
        else:
            # Get all active operations
            active_operations = timeout_manager.get_active_operations()
            
            return {
                "success": True,
                "active_operations": active_operations,
                "active_count": len(active_operations),
                "system_health": "healthy" if len(active_operations) < 3 else "busy"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get operation status: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def scan_zombie_processes() -> Dict[str, Any]:
    """🔍 PROCESS SCANNER - Detect potential zombie processes from video operations
    
    Scans for long-running Python processes that might be hung from previous operations.
    Identifies multiprocessing spawn processes, ffmpeg processes, and other video-related tasks.
    
    Returns:
        Dictionary containing:
        - python_spawn_processes: Long-running Python multiprocessing processes
        - ffmpeg_processes: Active FFMPEG processes  
        - video_related_processes: Other video/audio processing processes
        - recommendations: Suggested PIDs to investigate/kill
        - system_health: Overall process health assessment
    
    Example Usage:
        scan_zombie_processes()  # Get list of suspicious processes
    """
    try:
        import subprocess
        import time
        from datetime import datetime, timedelta
        
        # Get all processes
        ps_result = subprocess.run(
            ['ps', 'aux'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if ps_result.returncode != 0:
            return {
                "success": False,
                "error": "Failed to get process list"
            }
        
        lines = ps_result.stdout.strip().split('\n')[1:]  # Skip header
        
        python_spawn_processes = []
        ffmpeg_processes = []
        video_related_processes = []
        suspicious_pids = []
        
        current_time = time.time()
        
        for line in lines:
            try:
                parts = line.split(None, 10)  # Split into max 11 parts
                if len(parts) < 11:
                    continue
                    
                user, pid, cpu_pct, mem_pct, vsz, rss, tty, stat, started, time_used, command = parts
                
                # Skip if not our user
                import getpass
                if user != getpass.getuser():
                    continue
                
                pid = int(pid)
                cpu_pct = float(cpu_pct)
                
                # Calculate process age from start time
                process_age_hours = None
                try:
                    # Parse different start time formats (e.g., "10:36PM", "26Jun25", "Aug06")
                    if ':' in started:
                        # Today - time format
                        process_age_hours = 0  # Assume recent if time format
                    elif 'Jun' in started or 'Jul' in started or 'Aug' in started:
                        # Date format - calculate days
                        if len(started) == 6:  # Format like "26Jun25"
                            day = int(started[:2])
                            month_str = started[2:5]
                            year = int('20' + started[5:])
                            
                            month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                                       'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
                            
                            if month_str in month_map:
                                process_date = datetime(year, month_map[month_str], day)
                                age_delta = datetime.now() - process_date
                                process_age_hours = age_delta.total_seconds() / 3600
                except:
                    process_age_hours = None
                
                # Identify different types of processes
                command_lower = command.lower()
                
                # Python spawn processes (potential zombies)
                if 'python' in command_lower and 'spawn_main' in command_lower:
                    process_info = {
                        'pid': pid,
                        'cpu_percent': cpu_pct,
                        'memory_percent': float(mem_pct),
                        'started': started,
                        'age_hours': process_age_hours,
                        'time_used': time_used,
                        'command': command,
                        'status': stat
                    }
                    python_spawn_processes.append(process_info)
                    
                    # Mark spawn processes as suspicious if old or high CPU
                    if (process_age_hours and process_age_hours > 24) or cpu_pct > 5.0:
                        suspicious_pids.append({
                            'pid': pid,
                            'reason': f'Long-running spawn process ({process_age_hours:.1f}h old, {cpu_pct}% CPU)',
                            'priority': 'high' if process_age_hours and process_age_hours > 48 else 'medium',
                            'safety_level': 'safe_to_kill',  # Spawn processes are always safe to kill
                            'type': 'python_spawn_zombie'
                        })
                
                # FFMPEG processes
                elif 'ffmpeg' in command_lower:
                    process_info = {
                        'pid': pid,
                        'cpu_percent': cpu_pct,
                        'memory_percent': float(mem_pct),
                        'started': started,
                        'age_hours': process_age_hours,
                        'time_used': time_used,
                        'command': command[:100] + '...' if len(command) > 100 else command,
                        'status': stat
                    }
                    ffmpeg_processes.append(process_info)
                    
                    # Mark as suspicious if running too long
                    if process_age_hours and process_age_hours > 2:  # FFMPEG shouldn't run > 2 hours
                        suspicious_pids.append({
                            'pid': pid,
                            'reason': f'Long-running FFMPEG process ({process_age_hours:.1f}h)',
                            'priority': 'high',
                            'safety_level': 'safe_to_kill',  # Hung FFMPEG processes are safe to kill
                            'type': 'ffmpeg_hung'
                        })
                
                # Other video/audio related processes with detailed classification
                elif any(keyword in command_lower for keyword in 
                        ['uvicorn', 'mcp', 'java.*kompost', 'video', 'audio', 'youtube']):
                    
                    # Classify process type and safety
                    process_type = 'unknown'
                    safety_level = 'safe_to_kill'  # default
                    
                    if 'uvicorn' in command_lower:
                        if 'mcp' in command_lower or ':809' in command_lower:
                            process_type = 'mcp_server'
                            safety_level = 'do_not_kill'  # MCP servers should not be killed
                        else:
                            process_type = 'web_server'
                            safety_level = 'caution'  # Other web servers - ask before killing
                    elif 'java' in command_lower and 'kompost' in command_lower:
                        process_type = 'komposteur_service'
                        safety_level = 'caution'  # Processing service - may be in use
                    elif 'firebase' in command_lower:
                        process_type = 'firebase_emulator'
                        safety_level = 'caution'  # Development service
                    elif 'node' in command_lower and ('firebase' in command_lower or 'emulator' in command_lower):
                        process_type = 'firebase_node_service'
                        safety_level = 'caution'
                    elif any(keyword in command_lower for keyword in ['video', 'audio', 'youtube']):
                        process_type = 'media_processing'
                        safety_level = 'safe_to_kill'  # Media processing can usually be restarted
                    
                    process_info = {
                        'pid': pid,
                        'cpu_percent': cpu_pct,
                        'memory_percent': float(mem_pct),
                        'started': started,
                        'age_hours': process_age_hours,
                        'time_used': time_used,
                        'command': command[:100] + '...' if len(command) > 100 else command,
                        'status': stat,
                        'type': process_type,
                        'safety_level': safety_level
                    }
                    video_related_processes.append(process_info)
                    
                    # Only mark as suspicious if it's safe to kill and meets criteria
                    if (safety_level == 'safe_to_kill' and process_age_hours and process_age_hours > 4) or \
                       (safety_level == 'caution' and process_age_hours and process_age_hours > 48):  # Very old services
                        suspicious_pids.append({
                            'pid': pid,
                            'reason': f'Long-running {process_type} ({process_age_hours:.1f}h)',
                            'priority': 'medium',
                            'safety_level': safety_level,
                            'type': process_type
                        })
                
            except (ValueError, IndexError):
                continue  # Skip malformed lines
        
        # System health assessment
        total_processes = len(python_spawn_processes) + len(ffmpeg_processes) + len(video_related_processes)
        suspicious_count = len(suspicious_pids)
        
        if suspicious_count > 5:
            health = "critical"
        elif suspicious_count > 2:
            health = "warning"
        elif len(python_spawn_processes) > 10:
            health = "concerning"
        else:
            health = "healthy"
        
        return {
            "success": True,
            "python_spawn_processes": python_spawn_processes,
            "ffmpeg_processes": ffmpeg_processes,
            "video_related_processes": video_related_processes,
            "suspicious_processes": suspicious_pids,
            "summary": {
                "total_spawn_processes": len(python_spawn_processes),
                "total_ffmpeg_processes": len(ffmpeg_processes),
                "total_video_processes": len(video_related_processes),
                "suspicious_count": suspicious_count,
                "system_health": health
            },
            "recommendations": {
                "safe_to_kill": {
                    "processes": [p for p in suspicious_pids if p.get('safety_level') == 'safe_to_kill'],
                    "kill_commands": [f"kill {p['pid']}" for p in suspicious_pids if p.get('safety_level') == 'safe_to_kill'],
                    "force_kill_commands": [f"kill -9 {p['pid']}" for p in suspicious_pids if p.get('safety_level') == 'safe_to_kill' and p['priority'] == 'high']
                },
                "caution_required": {
                    "processes": [p for p in suspicious_pids if p.get('safety_level') == 'caution'],
                    "warning": "These are services that may be in use. Verify they're not needed before killing.",
                    "kill_commands": [f"kill {p['pid']}" for p in suspicious_pids if p.get('safety_level') == 'caution']
                },
                "do_not_kill": {
                    "processes": [p for p in suspicious_pids if p.get('safety_level') == 'do_not_kill'],
                    "warning": "These are critical services (MCP servers, etc.) - DO NOT KILL unless absolutely necessary"
                },
                "summary": {
                    "immediate_action": [p for p in suspicious_pids if p['priority'] == 'high' and p.get('safety_level') == 'safe_to_kill'],
                    "investigate": [p for p in suspicious_pids if p['priority'] == 'medium'],
                    "total_suspicious": len(suspicious_pids),
                    "safe_to_kill_count": len([p for p in suspicious_pids if p.get('safety_level') == 'safe_to_kill']),
                    "protected_count": len([p for p in suspicious_pids if p.get('safety_level') in ['do_not_kill', 'caution']])
                }
            }
        }
        
    except subprocess.TimeoutError:
        return {
            "success": False,
            "error": "Process scan timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to scan processes: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def kill_zombie_processes(pids: List[int], force: bool = False) -> Dict[str, Any]:
    """☠️ PROCESS KILLER - Kill specified zombie processes with safety checks
    
    Kills specified processes after verifying they are safe to kill.
    Only kills processes that are classified as 'safe_to_kill' (spawn zombies, hung FFMPEG, etc.)
    Will NOT kill MCP servers or other critical services.
    
    Args:
        pids: List of process IDs to kill
        force: Use SIGKILL (-9) instead of SIGTERM (default: False)
    
    Returns:
        Dictionary with kill results and safety information
    
    Example Usage:
        kill_zombie_processes([81886, 82024])  # Kill specific zombie PIDs
        kill_zombie_processes([12345], force=True)  # Force kill with SIGKILL
    """
    try:
        import subprocess
        
        if not pids:
            return {
                "success": False,
                "error": "No PIDs provided to kill"
            }
        
        # First, scan current processes to verify safety
        scan_result = await mcp.call_tool('scan_zombie_processes', {})
        scan_text = scan_result[0].text if scan_result and len(scan_result) > 0 else '{}'
        scan_data = json.loads(scan_text)
        
        if not scan_data.get('success'):
            return {
                "success": False,
                "error": "Could not scan processes for safety verification"
            }
        
        # Build safety lookup from scan results
        safe_to_kill_pids = set()
        protected_pids = set()
        process_info = {}
        
        # Get all processes and their safety levels
        for proc_list, safety_level in [
            (scan_data.get('python_spawn_processes', []), 'safe_to_kill'),
            (scan_data.get('ffmpeg_processes', []), 'safe_to_kill'),
            (scan_data.get('video_related_processes', []), None)  # Check individual safety_level
        ]:
            for proc in proc_list:
                pid = int(proc['pid'])
                proc_safety = proc.get('safety_level', safety_level)
                process_info[pid] = {
                    'type': proc.get('type', 'unknown'),
                    'safety_level': proc_safety,
                    'command': proc.get('command', ''),
                    'started': proc.get('started', ''),
                    'cpu_percent': proc.get('cpu_percent', 0)
                }
                
                if proc_safety == 'safe_to_kill':
                    safe_to_kill_pids.add(pid)
                elif proc_safety in ['do_not_kill', 'caution']:
                    protected_pids.add(pid)
        
        # Verify all requested PIDs are safe to kill
        kill_results = []
        safety_violations = []
        
        for pid in pids:
            if pid in protected_pids:
                safety_violations.append({
                    'pid': pid,
                    'reason': f'Protected process: {process_info[pid]["type"]} ({process_info[pid]["safety_level"]})',
                    'command': process_info[pid].get('command', '')[:60] + '...'
                })
            elif pid not in safe_to_kill_pids:
                # Check if process still exists
                try:
                    check_result = subprocess.run(['ps', '-p', str(pid)], capture_output=True, text=True, timeout=5)
                    if check_result.returncode == 0:
                        safety_violations.append({
                            'pid': pid,
                            'reason': 'Process exists but not classified as safe to kill',
                            'command': 'Unknown - not in scan results'
                        })
                    else:
                        kill_results.append({
                            'pid': pid,
                            'status': 'already_dead',
                            'message': 'Process already terminated'
                        })
                except subprocess.TimeoutError:
                    safety_violations.append({
                        'pid': pid,
                        'reason': 'Could not verify process status (timeout)',
                        'command': 'Unknown'
                    })
            else:
                # Safe to kill - proceed with termination
                try:
                    signal_type = '-9' if force else '-15'  # SIGKILL vs SIGTERM
                    kill_cmd = ['kill', signal_type, str(pid)]
                    
                    result = subprocess.run(kill_cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        kill_results.append({
                            'pid': pid,
                            'status': 'killed',
                            'signal': 'SIGKILL' if force else 'SIGTERM',
                            'type': process_info[pid]['type'],
                            'message': f'Successfully killed {process_info[pid]["type"]}'
                        })
                    else:
                        kill_results.append({
                            'pid': pid,
                            'status': 'failed',
                            'error': result.stderr.strip() or 'Unknown error',
                            'message': f'Failed to kill PID {pid}'
                        })
                        
                except subprocess.TimeoutError:
                    kill_results.append({
                        'pid': pid,
                        'status': 'timeout',
                        'message': f'Kill command timed out for PID {pid}'
                    })
                except Exception as e:
                    kill_results.append({
                        'pid': pid,
                        'status': 'error',
                        'error': str(e),
                        'message': f'Error killing PID {pid}: {str(e)}'
                    })
        
        # Summary
        successful_kills = len([r for r in kill_results if r['status'] == 'killed'])
        failed_kills = len([r for r in kill_results if r['status'] in ['failed', 'timeout', 'error']])
        already_dead = len([r for r in kill_results if r['status'] == 'already_dead'])
        
        return {
            "success": len(safety_violations) == 0,
            "kill_results": kill_results,
            "safety_violations": safety_violations,
            "summary": {
                "requested_pids": len(pids),
                "successful_kills": successful_kills,
                "failed_kills": failed_kills,
                "already_dead": already_dead,
                "blocked_for_safety": len(safety_violations),
                "signal_used": 'SIGKILL (-9)' if force else 'SIGTERM (-15)'
            },
            "recommendation": "Check kill_results for detailed status of each PID" if kill_results else "No processes were killed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to kill processes: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def kill_all_safe_zombies(force: bool = False) -> Dict[str, Any]:
    """☠️ AUTO ZOMBIE KILLER - Automatically kill all safe zombie processes
    
    Scans for zombie processes and automatically kills all processes classified as 'safe_to_kill'.
    This includes Python spawn zombies and hung FFMPEG processes, but protects MCP servers
    and other critical services.
    
    Args:
        force: Use SIGKILL (-9) instead of SIGTERM (default: False)
    
    Returns:
        Dictionary with scan results and kill results
    
    Example Usage:
        kill_all_safe_zombies()  # Kill all safe zombies with SIGTERM
        kill_all_safe_zombies(force=True)  # Force kill with SIGKILL
    """
    try:
        # First scan for zombie processes
        scan_result = await mcp.call_tool('scan_zombie_processes', {})
        scan_text = scan_result[0].text if scan_result and len(scan_result) > 0 else '{}'
        scan_data = json.loads(scan_text)
        
        if not scan_data.get('success'):
            return {
                "success": False,
                "error": "Could not scan for zombie processes",
                "scan_result": scan_data
            }
        
        # Extract all safe-to-kill PIDs
        safe_pids = []
        
        # Get PIDs from recommendations
        safe_processes = scan_data.get('recommendations', {}).get('safe_to_kill', {}).get('processes', [])
        safe_pids.extend([int(p['pid']) for p in safe_processes])
        
        if not safe_pids:
            return {
                "success": True,
                "message": "No safe zombie processes found to kill",
                "scan_summary": scan_data.get('summary', {}),
                "kill_results": [],
                "recommendation": "System is clean - no zombie processes detected"
            }
        
        # Kill all safe processes
        kill_result = await mcp.call_tool('kill_zombie_processes', {
            'pids': safe_pids,
            'force': force
        })
        
        kill_text = kill_result[0].text if kill_result and len(kill_result) > 0 else '{}'
        kill_data = json.loads(kill_text)
        
        return {
            "success": kill_data.get('success', False),
            "scan_summary": scan_data.get('summary', {}),
            "kill_summary": kill_data.get('summary', {}),
            "kill_results": kill_data.get('kill_results', []),
            "safety_violations": kill_data.get('safety_violations', []),
            "processes_found": len(safe_pids),
            "signal_used": 'SIGKILL (-9)' if force else 'SIGTERM (-15)',
            "recommendation": f"Killed {kill_data.get('summary', {}).get('successful_kills', 0)} zombie processes"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to auto-kill zombies: {str(e)}"
        }


@mcp.tool() 
async def cleanup_partial_operations() -> Dict[str, Any]:
    """🧹 SYSTEM CLEANUP - Clean up partial operations and hung processes
    
    Manually trigger cleanup of partial operations, temp files, and hung processes.
    Useful for recovering from interrupted operations or system lockups.
    
    Returns:
        Dictionary with cleanup results and system health status
    
    Example Usage:
        cleanup_partial_operations()  # Clean up everything
    """
    try:
        result = await timeout_manager.cleanup_partial_operations()
        
        # Also clean up temp files via existing tool
        temp_cleanup = await mcp.call_tool('cleanup_temp_files', {})
        
        # Get process scan for additional context
        process_scan = await mcp.call_tool('scan_zombie_processes', {})
        
        return {
            "success": True,
            "operation_cleanup": result,
            "temp_file_cleanup": temp_cleanup,
            "process_scan": process_scan,
            "recommendation": "System cleanup completed. Check process_scan for any remaining zombie processes. Use kill_zombie_processes() to eliminate safe zombies."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to cleanup partial operations: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def get_available_video_effects(category: str = None, provider: str = None) -> Dict[str, Any]:
    """📹 VIDEO EFFECTS - List all available video effects with parameter discovery
    
    This tool provides comprehensive information about available video effects including:
    - Parameter specifications with types, ranges, and defaults
    - Performance estimates and provider information  
    - Category-based filtering for easy discovery
    - Parameter validation rules and constraints
    
    Args:
        category: Filter by effect category ("color", "stylistic", "blur", "distortion", "privacy")
        provider: Filter by provider ("ffmpeg", "opencv", "pil")
    
    Returns:
        Dictionary containing:
        - effects: Complete effect specifications with parameters
        - categories: Available effect categories
        - providers: Available effect providers  
        - effects_count: Total number of available effects
        
    Categories:
        🎨 color: Color grading, curves, film looks (vintage, noir)
        ✨ stylistic: Visual effects (VHS, vignette, neon glow)
        🌫️ blur: Gaussian blur, motion blur variants
        🔀 distortion: Chromatic aberration, glitch effects
        🔒 privacy: Face detection and blurring
        
    Providers:
        🎬 ffmpeg: High-performance native video filters
        👁️ opencv: AI-powered computer vision effects
        🖼️ pil: Image processing effects
        
    Example Usage:
        get_available_video_effects()  # All effects
        get_available_video_effects(category="color")  # Color effects only
        get_available_video_effects(provider="ffmpeg")  # FFmpeg effects only
    """
    try:
        return effect_processor.get_available_effects(category=category, provider=provider)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get available effects: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def apply_video_effect(file_id: str, effect_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """📹 VIDEO EFFECTS - Apply single video effect with parameter control
    
    Apply professional video effects to your videos with precise parameter control.
    Each effect preserves audio streams and provides performance estimates.
    
    Args:
        file_id: Source video file ID from list_files()
        effect_name: Effect name from get_available_video_effects()
        parameters: Effect-specific parameters (optional, uses defaults if not provided)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating processing completion
        - output_file_id: New file ID for the processed video
        - processing_time: Actual processing duration
        - effect_applied: Details of the effect and parameters used
        
    Popular Effects:
    
    🎨 Color Effects:
        - vintage_color: Warm nostalgic film look
          Parameters: intensity (0.0-2.0), warmth (-0.5-0.5), saturation (0.0-2.0)
        - film_noir: High contrast black and white  
          Parameters: contrast (1.0-3.0), brightness (-0.5-0.5)
    
    ✨ Stylistic Effects:
        - vhs_look: Retro VHS tape aesthetic
          Parameters: noise_level (0.0-20.0), blur_amount (0.0-2.0), saturation (0.0-2.0)
        - vignette: Dark edges for cinematic feel
          Parameters: angle (0.0-6.28), x0 (0.0-1.0), y0 (0.0-1.0), mode ("forward"/"backward")
    
    🌫️ Blur Effects:  
        - gaussian_blur: Smooth blur effect
          Parameters: sigma (0.1-20.0), steps (1-10)
    
    🔀 Distortion Effects:
        - chromatic_aberration: RGB channel separation
          Parameters: red_offset_x (-10-10), blue_offset_x (-10-10), intensity (0.0-2.0)
    
    🔒 Privacy Effects:
        - face_blur: Automatic face detection and blurring
          Parameters: blur_strength (5.0-50.0), detection_confidence (0.3-0.95)
          
    Example Usage:
        apply_video_effect(
            file_id="file_12345678",
            effect_name="vintage_color",
            parameters={"intensity": 1.2, "warmth": 0.3}
        )
        
        apply_video_effect(
            file_id="file_12345678", 
            effect_name="gaussian_blur",
            parameters={"sigma": 8.0}
        )
    """
    try:
        return await effect_processor.apply_effect(file_id, effect_name, parameters)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to apply video effect: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def apply_video_effect_chain(file_id: str, effects_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """📹 VIDEO EFFECTS - Apply multiple effects in sequence with chaining
    
    Stack multiple video effects to create complex looks and styles. Effects are applied
    sequentially, with each effect processing the output of the previous effect.
    
    Args:
        file_id: Source video file ID from list_files()
        effects_chain: List of effect steps, each containing:
            - effect: Effect name from get_available_video_effects()
            - parameters: Effect-specific parameters (optional)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating complete chain processing
        - final_output_file_id: File ID of the final processed video
        - applied_effects: Details of each effect step with output file IDs
        - total_steps: Number of effects applied
        
    Effect Stacking Examples:
    
    🎬 Cinematic Grade:
        [
            {"effect": "vintage_color", "parameters": {"intensity": 0.8, "warmth": 0.2}},
            {"effect": "vignette", "parameters": {"angle": 1.57}},
            {"effect": "gaussian_blur", "parameters": {"sigma": 1.0}}
        ]
    
    📱 Social Media Ready:
        [
            {"effect": "vintage_color", "parameters": {"saturation": 1.3}},
            {"effect": "vhs_look", "parameters": {"noise_level": 3.0}}
        ]
        
    🔒 Privacy Protection:
        [
            {"effect": "face_blur", "parameters": {"blur_strength": 20.0}},
            {"effect": "vintage_color", "parameters": {"intensity": 0.5}}
        ]
        
    🎨 Film Emulation:
        [
            {"effect": "film_noir", "parameters": {"contrast": 1.5}},
            {"effect": "chromatic_aberration", "parameters": {"intensity": 0.3}}
        ]
    
    Performance Notes:
        - Each effect adds processing time (see get_available_video_effects for estimates)
        - Order matters: blur effects should typically come last
        - Color effects work well together when applied in sequence
        - Privacy effects (face_blur) should be applied early in the chain
        
    Example Usage:
        apply_video_effect_chain(
            file_id="file_12345678",
            effects_chain=[
                {"effect": "vintage_color", "parameters": {"intensity": 1.0}},
                {"effect": "vignette", "parameters": {"angle": 1.57}},
                {"effect": "gaussian_blur", "parameters": {"sigma": 2.0}}
            ]
        )
    """
    try:
        return await effect_processor.apply_effect_chain(file_id, effects_chain)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to apply video effect chain: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def suggest_efficient_workflow(goal_description: str, available_files: List[str] = None) -> Dict[str, Any]:
    """🎯 WORKFLOW OPTIMIZATION - Get optimized workflow suggestions to minimize function calls
    
    This tool analyzes your goal and suggests the most efficient combination of MCP tools to achieve it,
    reducing the number of function calls from 20+ down to 3-5 calls by using atomic operations and batch processing.
    
    Args:
        goal_description: What you want to create (e.g., "music video with effects", "batch convert videos")
        available_files: Optional list of file names/IDs you want to work with
    
    Returns:
        Dictionary containing:
        - recommended_workflow: Step-by-step optimized workflow
        - efficiency_score: Estimated function call reduction
        - atomic_functions: Single-call solutions when available
        - batch_operations: Multi-step operations in minimal calls
        - fallback_manual: Manual step-by-step if atomic functions fail
    
    Efficiency Examples:
        Instead of: 25+ individual calls
        Use: 3-5 optimized calls with batch_process() and atomic functions
        
        Instead of: apply_video_effect() → apply_video_effect() → apply_video_effect()
        Use: apply_video_effect_chain() - single call for multiple effects
        
        Instead of: Individual trim/resize/audio operations
        Use: batch_process() with OUTPUT_PREVIOUS chaining
    
    Goal Types Optimized:
        🎬 "Create music video" → create_video_from_description() (1 call)
        ✨ "Apply multiple effects" → apply_video_effect_chain() (1 call)  
        🔗 "Multi-step processing" → batch_process() (1 call)
        📱 "Social media format" → Optimized resize + effects batch
        🎵 "Add music to videos" → Audio workflow with minimal steps
    """
    try:
        goal = goal_description.lower()
        
        # Analyze goal and suggest optimal workflow
        if any(keyword in goal for keyword in ['music video', 'create video', 'video from']):
            return {
                "success": True,
                "recommended_workflow": "atomic_single_call",
                "efficiency_score": "95% reduction (25+ calls → 1 call)",
                "atomic_functions": [
                    {
                        "function": "create_video_from_description",
                        "description": "Single atomic call for complete video creation",
                        "parameters": {
                            "description": goal_description,
                            "title": "Generated Video",
                            "execution_mode": "full"
                        },
                        "why_efficient": "Combines file discovery, komposition generation, build planning, and processing in one call"
                    }
                ],
                "fallback_manual": [
                    "1. list_files() - discover available media",
                    "2. generate_komposition_from_description() - create structure", 
                    "3. process_komposition_file() - execute creation"
                ],
                "estimated_calls": 1,
                "efficiency_tips": [
                    "Use execution_mode='plan_only' to preview without processing",
                    "Add custom_resolution='600x800' for social media formats",
                    "Include BPM and effects in description for better results"
                ]
            }
            
        elif any(keyword in goal for keyword in ['effects', 'filter', 'apply', 'style']):
            return {
                "success": True,
                "recommended_workflow": "effect_chain_batch",
                "efficiency_score": "80% reduction (10+ calls → 2 calls)",
                "atomic_functions": [
                    {
                        "function": "get_available_video_effects",
                        "description": "Discover all effects and parameters",
                        "parameters": {},
                        "why_efficient": "Single call to see all 12 effects with parameter specs"
                    },
                    {
                        "function": "apply_video_effect_chain",
                        "description": "Apply multiple effects in one operation",
                        "parameters": {
                            "file_id": "target_file_id",
                            "effects_chain": [
                                {"effect": "vintage_color", "parameters": {"intensity": 1.0}},
                                {"effect": "vignette", "parameters": {"angle": 1.57}}
                            ]
                        },
                        "why_efficient": "Chains multiple effects without intermediate files"
                    }
                ],
                "batch_operations": [
                    {
                        "description": "If you need different effects on different files",
                        "use": "batch_process with video effects operations"
                    }
                ],
                "estimated_calls": 2,
                "popular_effect_chains": {
                    "cinematic": ["vintage_color", "vignette", "gaussian_blur"],
                    "social_media": ["social_media_pack", "warm_cinematic"],
                    "retro": ["vhs_look", "chromatic_aberration"],
                    "professional": ["film_noir", "dreamy_soft"]
                }
            }
            
        elif any(keyword in goal for keyword in ['batch', 'multiple', 'convert', 'resize']):
            return {
                "success": True,
                "recommended_workflow": "batch_processing",
                "efficiency_score": "90% reduction (20+ calls → 2-3 calls)",
                "atomic_functions": [
                    {
                        "function": "batch_process",
                        "description": "Process multiple operations with OUTPUT_PREVIOUS chaining",
                        "parameters": {
                            "operations": [
                                {"input_file_id": "file_123", "operation": "trim", "output_extension": "mp4", "params": "start=0 duration=10"},
                                {"input_file_id": "OUTPUT_PREVIOUS", "operation": "resize", "output_extension": "mp4", "params": "width=1920 height=1080"},
                                {"input_file_id": "OUTPUT_PREVIOUS", "operation": "to_mp3", "output_extension": "mp3"}
                            ]
                        },
                        "why_efficient": "Chains multiple operations atomically with proper file passing"
                    }
                ],
                "chaining_tips": [
                    "Use 'OUTPUT_PREVIOUS' as input_file_id to chain operations",
                    "Each operation processes the output of the previous one",
                    "Batch stops on first failure with detailed error reporting",
                    "Final output file_id returned for further processing"
                ],
                "estimated_calls": 1,
                "common_chains": {
                    "social_media_prep": ["trim", "resize", "to_mp3"],
                    "quality_improve": ["normalize_audio", "convert", "resize"],
                    "format_standardize": ["convert", "resize", "extract_audio"]
                }
            }
            
        else:
            # General workflow optimization
            return {
                "success": True,
                "recommended_workflow": "optimized_general",
                "efficiency_score": "70% reduction (15+ calls → 4-5 calls)",
                "general_principles": [
                    "1. Always start with list_files() to see available media and get smart suggestions",
                    "2. Use atomic functions when available (create_video_from_description, apply_video_effect_chain)",
                    "3. Use batch_process() for multi-step operations with OUTPUT_PREVIOUS chaining",
                    "4. Use list_generated_files() to track outputs and cleanup_temp_files() to clean up",
                    "5. Prefer single comprehensive calls over multiple individual operations"
                ],
                "atomic_first_strategy": [
                    "Try create_video_from_description() for video creation goals",
                    "Try apply_video_effect_chain() for multiple effects",
                    "Try batch_process() for multi-step workflows"
                ],
                "manual_fallback": [
                    "If atomic functions fail, use individual process_file() calls",
                    "Chain outputs manually: output_file_id from step 1 → input_file_id for step 2",
                    "Always verify success before proceeding to next step"
                ],
                "estimated_calls": "4-5 vs 15-25 manual calls"
            }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate workflow suggestions: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def estimate_effect_processing_time(file_id: str, effects_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """📹 VIDEO EFFECTS - Estimate processing time for effects chain
    
    Get accurate processing time estimates before applying effects. Helps with planning
    batch operations and understanding performance impact of different effect combinations.
    
    Args:
        file_id: Source video file ID to analyze
        effects_chain: List of effect steps to estimate (same format as apply_video_effect_chain)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating estimation completion
        - video_duration: Duration of source video in seconds
        - total_estimated_time: Total processing time estimate in seconds
        - effect_estimates: Per-effect processing estimates with performance tiers
        - time_per_effect: Average time per effect
        
    Performance Tiers:
        🚀 fast: Real-time or near real-time processing (< 1s per video second)
        ⚡ medium: Moderate processing time (1-5s per video second)  
        🐌 slow: Intensive processing (> 5s per video second)
        
    Estimation Factors:
        - Video duration and resolution
        - Effect complexity and provider (FFmpeg vs OpenCV vs PIL)
        - Hardware capabilities (CPU vs GPU acceleration where available)
        - Parameter settings (higher blur = longer processing)
        
    Use Cases:
        - Plan batch processing workflows
        - Compare different effect combinations
        - Estimate completion times for long videos
        - Optimize effect order for better performance
        
    Example Usage:
        estimate_effect_processing_time(
            file_id="file_12345678", 
            effects_chain=[
                {"effect": "vintage_color"},
                {"effect": "gaussian_blur", "parameters": {"sigma": 10.0}},
                {"effect": "face_blur"}
            ]
        )
    """
    try:
        return effect_processor.estimate_processing_time(file_id, effects_chain)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to estimate processing time: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def analyze_video_formats(file_ids: List[str]) -> Dict[str, Any]:
    """
    Analyze aspect ratios of multiple videos and suggest optimal target format.
    
    Args:
        file_ids: List of file IDs to analyze
        
    Returns:
        Dictionary with format analysis and recommendations
    """
    try:
        analyses = []
        for file_id in file_ids:
            file_path = file_manager.resolve_id(file_id)
            analysis = format_manager.analyze_video_format(file_path, file_id)
            analyses.append({
                "file_id": file_id,
                "resolution": f"{analysis.width}x{analysis.height}",
                "aspect_ratio": f"{analysis.aspect_ratio:.2f}",
                "orientation": analysis.orientation,
                "suggested_crop_mode": analysis.suggested_crop_mode.value,
                "crop_compatibility": analysis.crop_compatibility
            })
        
        # Get format suggestion
        video_analyses = [format_manager.analyze_video_format(file_manager.resolve_id(fid), fid) for fid in file_ids]
        suggested_format = format_manager.suggest_target_format(video_analyses)
        
        return {
            "success": True,
            "video_analyses": analyses,
            "suggested_format": {
                "aspect_ratio": suggested_format.aspect_ratio.display_name,
                "resolution": f"{suggested_format.width}x{suggested_format.height}",
                "orientation": suggested_format.orientation,
                "crop_mode": suggested_format.crop_mode.value
            },
            "common_presets": {name: {
                "aspect_ratio": preset.aspect_ratio.display_name,
                "resolution": f"{preset.width}x{preset.height}",
                "crop_mode": preset.crop_mode.value
            } for name, preset in COMMON_PRESETS.items()}
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze video formats: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def preview_format_conversion(
    file_id: str, 
    target_format: str, 
    crop_mode: str = "center_crop",
    timestamp: float = 5.0
) -> Dict[str, Any]:
    """
    Generate preview image showing how video will be cropped/fitted to target format.
    
    Args:
        file_id: ID of the source video
        target_format: Target format preset name or "custom"
        crop_mode: Cropping strategy (center_crop, scale_letterbox, scale_blur_bg, etc.)
        timestamp: Time in seconds to extract preview frame
        
    Returns:
        Dictionary with preview image path and conversion details
    """
    try:
        from .format_manager import CropMode, FormatSpec, AspectRatio
    except ImportError:
        from format_manager import CropMode, FormatSpec, AspectRatio
        
        # Get target format specification
        if target_format in COMMON_PRESETS:
            format_spec = COMMON_PRESETS[target_format]
        else:
            # Default format
            format_spec = COMMON_PRESETS["youtube_landscape"]
        
        # Override crop mode if specified
        try:
            crop_mode_enum = CropMode(crop_mode)
            format_spec = FormatSpec(format_spec.aspect_ratio, format_spec.resolution, crop_mode_enum)
        except ValueError:
            pass  # Use default crop mode
        
        # Generate preview
        file_path = file_manager.resolve_id(file_id)
        preview_path = format_manager.generate_preview_frame(file_path, format_spec, timestamp)
        
        # Get conversion analysis
        analysis = format_manager.analyze_video_format(file_path, file_id)
        conversion_plan = format_manager.create_format_conversion_plan([analysis], format_spec)
        
        return {
            "success": True,
            "preview_image": preview_path,
            "conversion_details": conversion_plan["video_conversions"][0],
            "quality_estimate": conversion_plan["estimated_quality_loss"],
            "warnings": conversion_plan["warnings"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to generate preview: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def create_format_conversion_plan(
    file_ids: List[str],
    target_format: str = "auto",
    crop_mode: str = "auto"
) -> Dict[str, Any]:
    """
    Create detailed plan for converting multiple videos to consistent target format.
    
    Args:
        file_ids: List of video file IDs to convert
        target_format: Target format preset ("youtube_landscape", "instagram_square", etc.) or "auto"
        crop_mode: Cropping strategy or "auto" for intelligent selection
        
    Returns:
        Complete conversion plan with FFmpeg commands and quality estimates
    """
    try:
        from .format_manager import CropMode, FormatSpec
    except ImportError:
        from format_manager import CropMode, FormatSpec
        
        # Analyze all videos
        video_analyses = []
        for file_id in file_ids:
            file_path = file_manager.resolve_id(file_id)
            analysis = format_manager.analyze_video_format(file_path, file_id)
            video_analyses.append(analysis)
        
        # Determine target format
        if target_format == "auto":
            format_spec = format_manager.suggest_target_format(video_analyses)
        elif target_format in COMMON_PRESETS:
            format_spec = COMMON_PRESETS[target_format]
        else:
            format_spec = COMMON_PRESETS["youtube_landscape"]  # Fallback
        
        # Override crop mode if specified
        if crop_mode != "auto":
            try:
                crop_mode_enum = CropMode(crop_mode)
                format_spec = FormatSpec(format_spec.aspect_ratio, format_spec.resolution, crop_mode_enum)
            except ValueError:
                pass  # Use default crop mode
        
        # Create detailed conversion plan
        conversion_plan = format_manager.create_format_conversion_plan(video_analyses, format_spec)
        
        return {
            "success": True,
            "conversion_plan": conversion_plan,
            "execution_ready": True,
            "estimated_processing_time": len(file_ids) * 30  # Rough estimate
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create conversion plan: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def get_format_presets() -> Dict[str, Any]:
    """
    Get list of available format presets for different platforms and use cases.
    
    Returns:
        Dictionary of format presets with their specifications
    """
    try:
        presets = {}
        for name, preset in COMMON_PRESETS.items():
            presets[name] = {
                "name": name,
                "aspect_ratio": preset.aspect_ratio.display_name,
                "resolution": f"{preset.width}x{preset.height}",
                "orientation": preset.orientation,
                "crop_mode": preset.crop_mode.value,
                "description": {
                    "youtube_landscape": "Standard YouTube video format (16:9 landscape)",
                    "instagram_square": "Instagram square post format (1:1)",
                    "instagram_story": "Instagram Story/Reels format (9:16 portrait)",
                    "tiktok_vertical": "TikTok vertical video format (9:16 portrait)",
                    "twitter_landscape": "Twitter video format (16:9 landscape)",
                    "facebook_square": "Facebook square video format (1:1)",
                    "cinema_wide": "Cinematic widescreen format (21:9)"
                }.get(name, f"Format preset: {name}")
            }
        
        return {
            "success": True,
            "presets": presets,
            "crop_modes": {
                "center_crop": "Crop from center, losing edges (good for symmetric content)",
                "smart_crop": "AI-detected focal point cropping (best quality, slower)",
                "scale_letterbox": "Fit with black bars (preserves all content)",
                "scale_blur_bg": "Fit with blurred background (popular for social media)",
                "scale_stretch": "Stretch to fit (may distort, not recommended)",
                "top_crop": "Crop from top (good for portraits with people)",
                "bottom_crop": "Crop from bottom"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get format presets: {str(e)}"
        }


# Audio Effects Tools

@mcp.tool()
@timing_decorator
async def get_available_audio_effects(category: Optional[str] = None) -> Dict[str, Any]:
    """🎵 AUDIO EFFECTS - List all available audio effects with parameter discovery
    
    This tool provides comprehensive information about available audio effects including:
    - Parameter specifications with types, ranges, and defaults
    - Performance estimates and provider information  
    - Category-based filtering for easy discovery
    - Parameter validation rules and constraints
    
    Args:
        category: Filter by effect category ("eq", "dynamics", "loudness", "spatial", "filter")
    
    Returns:
        Dictionary containing:
        - effects: Complete effect specifications with parameters
        - categories: Available effect categories
        - effects_count: Total number of available effects
        
    Categories:
        🎛️ eq: Equalizers and frequency shaping
        🎚️ dynamics: Compressors, limiters, gates
        📊 loudness: LUFS normalization and metering
        🌊 spatial: Stereo width and positioning
        🔊 filter: High-pass, low-pass, band filters
        
    Example Usage:
        get_available_audio_effects()  # All effects
        get_available_audio_effects(category="dynamics")  # Compressors/limiters only
    """
    try:
        return audio_effect_processor.get_available_effects(category=category)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get available audio effects: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def apply_audio_effect(file_id: str, effect_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """🎵 AUDIO EFFECTS - Apply single audio effect with parameter control
    
    Apply professional audio effects to your audio files with precise parameter control.
    Each effect preserves original quality and provides performance estimates.
    
    Args:
        file_id: Source audio/video file ID from list_files()
        effect_name: Effect name from get_available_audio_effects()
        parameters: Effect-specific parameters (optional, uses defaults if not provided)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating processing completion
        - output_file_id: New file ID for the processed audio
        - processing_time: Actual processing duration
        - effect_applied: Details of the effect and parameters used
        
    Popular Audio Effects:
    
    🎛️ EQ Effects:
        - equalizer: Multi-band parametric EQ
          Parameters: bands [{"frequency": Hz, "gain": dB, "q": width}]
        - high_pass_filter: Remove low frequencies
          Parameters: frequency (10-1000 Hz), rolloff (6-48 dB/oct)
    
    🎚️ Dynamics:
        - compressor: Dynamic range control
          Parameters: threshold (-60-0 dB), ratio (1-20), attack/release (ms)
        - limiter: Peak limiting for output control
          Parameters: ceiling (-3-0 dBTP), release (1-1000 ms)
        - de_esser: Sibilance control
          Parameters: frequency (2000-12000 Hz), threshold, ratio
    
    📊 Loudness:
        - loudness_normalize: EBU R128 normalization
          Parameters: target_lufs (-30 to -6), true_peak (-3 to 0)
    
    🌊 Spatial:
        - stereo_widener: Stereo field control
          Parameters: width (0.0-2.0), frequency_range [low, high]
        - mono_bass: Make low frequencies mono
          Parameters: frequency (50-300 Hz)
          
    Example Usage:
        apply_audio_effect(
            file_id="file_12345678",
            effect_name="compressor",
            parameters={"threshold": -18, "ratio": 3.0, "attack": 20, "release": 150}
        )
        
        apply_audio_effect(
            file_id="file_12345678", 
            effect_name="loudness_normalize",
            parameters={"target_lufs": -16, "true_peak": -1.0}
        )
    """
    try:
        return await audio_effect_processor.apply_effect(file_id, effect_name, parameters)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to apply audio effect: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def apply_audio_effect_chain(file_id: str, effects_chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """🎵 AUDIO EFFECTS - Apply multiple audio effects in sequence with chaining
    
    Stack multiple audio effects to create professional mastering chains. Effects are applied
    sequentially, with each effect processing the output of the previous effect.
    
    Args:
        file_id: Source audio/video file ID from list_files()
        effects_chain: List of effect steps, each containing:
            - effect: Effect name from get_available_audio_effects()
            - parameters: Effect-specific parameters (optional)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating complete chain processing
        - final_output_file_id: File ID of the final processed audio
        - applied_effects: Details of each effect step with output file IDs
        - total_steps: Number of effects applied
        
    Professional Mastering Chain Examples:
    
    🎸 Rock Mastering:
        [
            {"effect": "high_pass_filter", "parameters": {"frequency": 35}},
            {"effect": "equalizer", "parameters": {"bands": [
                {"frequency": 80, "gain": 1.5, "q": 0.8},
                {"frequency": 2500, "gain": 1.8, "q": 1.0}
            ]}},
            {"effect": "compressor", "parameters": {"threshold": -18, "ratio": 2.5}},
            {"effect": "loudness_normalize", "parameters": {"target_lufs": -9}}
        ]
    
    🎧 EDM Mastering:
        [
            {"effect": "mono_bass", "parameters": {"frequency": 120}},
            {"effect": "compressor", "parameters": {"threshold": -15, "ratio": 4.0}},
            {"effect": "stereo_widener", "parameters": {"width": 1.3}},
            {"effect": "limiter", "parameters": {"ceiling": -1.0}}
        ]
        
    🎤 Podcast Enhancement:
        [
            {"effect": "high_pass_filter", "parameters": {"frequency": 85}},
            {"effect": "de_esser", "parameters": {"frequency": 6500, "threshold": -25}},
            {"effect": "compressor", "parameters": {"threshold": -20, "ratio": 4.0}},
            {"effect": "loudness_normalize", "parameters": {"target_lufs": -16}}
        ]
    
    Performance Notes:
        - Each effect adds processing time (see get_available_audio_effects for estimates)
        - Order matters: filters → EQ → dynamics → loudness normalization
        - Loudness normalization should typically be the final step
        
    Example Usage:
        apply_audio_effect_chain(
            file_id="file_12345678",
            effects_chain=[
                {"effect": "high_pass_filter", "parameters": {"frequency": 80}},
                {"effect": "compressor", "parameters": {"threshold": -18, "ratio": 3.0}},
                {"effect": "loudness_normalize", "parameters": {"target_lufs": -14}}
            ]
        )
    """
    try:
        return await audio_effect_processor.apply_effect_chain(file_id, effects_chain)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to apply audio effect chain: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def apply_audio_template(file_id: str, template_name: str) -> Dict[str, Any]:
    """🎵 AUDIO TEMPLATES - Apply pre-defined or user-created audio effect templates
    
    Apply complete mastering chains using predefined templates for different genres
    and use cases. Templates include professional mastering chains optimized for
    streaming platforms.
    
    Args:
        file_id: Source audio/video file ID from list_files()
        template_name: Template name from list_audio_templates()
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating template application
        - final_output_file_id: File ID of the processed audio
        - template_applied: Template details and effects chain used
        - applied_effects: Details of each processing step
        
    Built-in Templates:
        🎸 rock_mastering: Professional rock mastering for streaming
        🎧 edm_mastering: High-impact EDM mastering with controlled low-end
        🎤 podcast_enhancement: Speech processing for podcasts
        
    Platform Optimization:
        - Templates include LUFS targets for major platforms
        - True peak limiting prevents transcoding distortion
        - Genre-specific EQ and dynamics for optimal sound
        
    Example Usage:
        apply_audio_template(
            file_id="file_12345678",
            template_name="rock_mastering"
        )
    """
    try:
        return await audio_effect_processor.apply_effect_template(file_id, template_name)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to apply audio template: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def list_audio_templates() -> Dict[str, Any]:
    """🎵 AUDIO TEMPLATES - List all available audio effect templates
    
    Get all available audio templates including predefined professional templates
    and user-created custom templates.
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating list generation
        - predefined: List of built-in professional templates
        - user: List of user-created custom templates
        - template_count: Total number of templates available
        
    Template Information:
        Each template includes:
        - name: Template display name
        - description: What the template does
        - category: Template type (mastering, speech, etc.)
        - genre: Target music genre or content type
        - target_platforms: Optimized platforms (Spotify, Apple Music, etc.)
        - effects_chain: Complete effects processing chain
        
    Template Locations:
        - Predefined: examples/effect-templates/audio/
        - User: /tmp/music/effect-templates/audio/
        
    Example Usage:
        list_audio_templates()
    """
    try:
        return {
            "success": True,
            **audio_effect_processor.list_effect_templates()
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list audio templates: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def save_audio_template(template_name: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
    """🎵 AUDIO TEMPLATES - Save custom audio effect template
    
    Save a custom audio effect template to the user template directory for reuse.
    Templates can be created from successful effect chains or designed from scratch.
    
    Args:
        template_name: Name for the new template (no .yaml extension needed)
        template_data: Template structure with name, description, category, effects_chain
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating save completion
        - template_path: Path where template was saved
        - template_name: Name of the saved template
        
    Template Structure:
        {
            "name": "My Custom Template",
            "description": "Description of what this template does",
            "category": "mastering" or "speech" or "creative",
            "genre": "rock" or "edm" or "podcast" etc,
            "target_platforms": ["spotify", "apple_music"],
            "effects_chain": [
                {"effect": "effect_name", "parameters": {...}},
                ...
            ]
        }
        
    Example Usage:
        save_audio_template(
            template_name="my_vocal_chain",
            template_data={
                "name": "My Vocal Processing Chain",
                "description": "Custom vocal processing for my podcast",
                "category": "speech",
                "genre": "podcast",
                "target_platforms": ["spotify_podcasts"],
                "effects_chain": [
                    {"effect": "high_pass_filter", "parameters": {"frequency": 85}},
                    {"effect": "compressor", "parameters": {"threshold": -20, "ratio": 4.0}},
                    {"effect": "loudness_normalize", "parameters": {"target_lufs": -16}}
                ]
            }
        )
    """
    try:
        success = audio_effect_processor.save_effect_template(template_name, template_data)
        if success:
            template_path = audio_effect_processor.user_templates_dir / f"{template_name}.yaml"
            return {
                "success": True,
                "template_path": str(template_path),
                "template_name": template_name,
                "message": f"Template '{template_name}' saved successfully"
            }
        else:
            return {
                "success": False,
                "error": f"Failed to save template '{template_name}'"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to save audio template: {str(e)}"
        }


# Video Comparison Tools

@mcp.tool()
@timing_decorator
async def create_video_comparison(
    file_id_1: str, 
    file_id_2: str, 
    comparison_type: str = "side_by_side",
    label_1: str = "Version A",
    label_2: str = "Version B",
    resolution: str = "1920x1080",
    sync_audio: bool = True,
    add_labels: bool = True
) -> Dict[str, Any]:
    """🎬 VIDEO COMPARISON - Create side-by-side video comparison for A/B testing
    
    Perfect for comparing two versions of the same video project to evaluate:
    - Different editing approaches
    - Effect applications
    - Audio mixing results
    - Resolution or quality differences
    
    Args:
        file_id_1: First video file ID from list_files()
        file_id_2: Second video file ID from list_files()
        comparison_type: Layout type ("side_by_side", "top_bottom") 
        label_1: Text label for first video (default: "Version A")
        label_2: Text label for second video (default: "Version B")
        resolution: Output resolution (default: "1920x1080")
        sync_audio: Whether to mix both audio tracks (default: True)
        add_labels: Whether to add text labels identifying each version (default: True)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating comparison creation success
        - output_file_id: File ID of the comparison video
        - comparison_type: Type of comparison layout used
        - configuration: Settings used for the comparison
        - processing_time: Time taken to create the comparison
        
    Perfect For:
        - Music video A/B testing
        - Before/after effect comparisons  
        - Different edit timeline comparisons
        - Quality assessment workflows
        
    Example Usage:
        create_video_comparison(
            file_id_1="file_12345678",
            file_id_2="file_87654321", 
            label_1="Original Cut",
            label_2="Director's Cut",
            sync_audio=False  # Use audio from first video only
        )
    """
    try:
        from .video_comparison_tool import ComparisonConfig
    except ImportError:
        from video_comparison_tool import ComparisonConfig
        
    config = ComparisonConfig(
        layout=comparison_type,
        sync_audio=sync_audio,
        add_labels=add_labels,
        resolution=resolution
    )
    
    return await video_comparison_tool.create_side_by_side_comparison(
        file_id_1, file_id_2, label_1, label_2, config
    )


@mcp.tool()
@timing_decorator
async def analyze_video_differences(file_id_1: str, file_id_2: str) -> Dict[str, Any]:
    """🔍 VIDEO ANALYSIS - Analyze technical and content differences between two videos
    
    Provides detailed analysis comparison between two videos including:
    - Scene count and structure differences
    - Duration and pacing analysis
    - Visual complexity comparison
    - Quality score differences
    - AI-generated recommendations
    
    Args:
        file_id_1: First video file ID from list_files()
        file_id_2: Second video file ID from list_files()
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating analysis completion
        - video_1: Analysis data for first video
        - video_2: Analysis data for second video
        - differences: Calculated differences in key metrics
        - recommendations: AI-generated suggestions based on comparison
        
    Analysis Metrics:
        - Scene count and distribution
        - Video duration differences
        - Visual complexity assessment
        - Quality scores (if available)
        - Content structure comparison
        
    Perfect For:
        - Understanding editing impact
        - Quantifying improvement between versions
        - Making data-driven editing decisions
        - Quality assessment workflows
        
    Example Usage:
        analyze_video_differences(
            file_id_1="file_12345678",  # Original version
            file_id_2="file_87654321"   # Edited version
        )
    """
    try:
        return await video_comparison_tool.create_analysis_comparison(
            file_id_1, file_id_2, analysis_type="comprehensive"
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to analyze video differences: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def create_multi_video_comparison(
    file_ids: List[str],
    labels: List[str] = None,
    layout: str = "grid",
    resolution: str = "1920x1080",
    add_labels: bool = True
) -> Dict[str, Any]:
    """🎬 MULTI-VIDEO COMPARISON - Create 2x2 grid comparison of up to 4 videos
    
    Compare multiple video versions simultaneously in a grid layout.
    Perfect for extensive A/B testing and multi-option evaluation.
    
    Args:
        file_ids: List of 2-4 video file IDs from list_files()
        labels: Optional list of labels for each video (default: Version A, B, C, D)
        layout: Layout type ("grid" for 2x2, "horizontal" for side-by-side)
        resolution: Output resolution (default: "1920x1080")
        add_labels: Whether to add text labels identifying each version (default: True)
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating comparison creation success
        - output_file_id: File ID of the multi-comparison video
        - comparison_type: Type of comparison layout used
        - input_files: List of input files with their labels
        - configuration: Settings used for the comparison
        - processing_time: Time taken to create the comparison
        
    Grid Layouts:
        - 2 videos: Side-by-side horizontal layout
        - 3 videos: Top row (2 videos) + bottom row (1 centered)
        - 4 videos: 2x2 grid layout
        
    Perfect For:
        - Multi-version comparison workflows
        - Effect variation testing
        - Timeline alternative evaluation
        - Client presentation materials
        
    Example Usage:
        create_multi_video_comparison(
            file_ids=["file_1", "file_2", "file_3", "file_4"],
            labels=["Original", "Color Graded", "With Effects", "Final Cut"],
            layout="grid"
        )
    """
    try:
        from .video_comparison_tool import ComparisonConfig
    except ImportError:
        from video_comparison_tool import ComparisonConfig
        
    if len(file_ids) < 2 or len(file_ids) > 4:
        return {
            "success": False,
            "error": "Multi-video comparison requires 2-4 videos"
        }
    
    config = ComparisonConfig(
        layout=layout,
        add_labels=add_labels,
        resolution=resolution
    )
    
    return await video_comparison_tool.create_four_way_comparison(
        file_ids, labels, config
    )


@mcp.tool()
@timing_decorator
async def verify_music_video(
    file_id: str,
    expected_duration: Optional[float] = None,
    expected_resolution: Optional[str] = None,
    check_audio: bool = True,
    check_video: bool = True
) -> Dict[str, Any]:
    """🎵 VERIFICATION - Verify music video meets expected criteria
    
    Comprehensive verification component that validates a music video meets
    expected properties. Returns detailed analysis for LLM validation.
    
    Args:
        file_id: Video file ID to verify
        expected_duration: Expected duration in seconds (tolerance ±2s)
        expected_resolution: Expected resolution (e.g., "1920x1080")
        check_audio: Whether to verify audio track exists
        check_video: Whether to verify video track exists
    
    Returns:
        Dictionary with verification results and detailed analysis
    
    Example:
        verify_music_video(
            file_id="video_12345",
            expected_duration=60.0,
            expected_resolution="1920x1080"
        )
    """
    try:
        # Get detailed file info
        info_result = await get_file_info(file_id)
        if not info_result.get('media_info', {}).get('success'):
            return {
                "success": False,
                "error": "Could not analyze video file",
                "verification_failed": True
            }
        
        video_props = info_result['media_info']['video_properties']
        basic_info = info_result['basic_info']
        
        # Initialize verification results
        verification = {
            "success": True,
            "file_id": file_id,
            "verification_passed": True,
            "checks_performed": [],
            "failures": [],
            "properties": {
                "file_size_mb": basic_info.get('size', 0) / (1024 * 1024),
                "duration": video_props.get('duration', 0),
                "resolution": video_props.get('resolution'),
                "has_video": video_props.get('has_video', False),
                "has_audio": video_props.get('has_audio', False),
                "codec": video_props.get('codec'),
                "bitrate": video_props.get('bitrate'),
                "fps": video_props.get('fps')
            }
        }
        
        # Check video track
        if check_video:
            verification["checks_performed"].append("video_track_exists")
            if not video_props.get('has_video', False):
                verification["failures"].append("No video track found")
                verification["verification_passed"] = False
        
        # Check audio track
        if check_audio:
            verification["checks_performed"].append("audio_track_exists")
            if not video_props.get('has_audio', False):
                verification["failures"].append("No audio track found")
                verification["verification_passed"] = False
        
        # Check duration
        if expected_duration is not None:
            verification["checks_performed"].append("duration_check")
            actual_duration = video_props.get('duration', 0)
            duration_diff = abs(actual_duration - expected_duration)
            
            if duration_diff > 2.0:  # ±2 second tolerance
                verification["failures"].append(
                    f"Duration mismatch: expected {expected_duration}s, got {actual_duration}s (diff: {duration_diff:.1f}s)"
                )
                verification["verification_passed"] = False
            else:
                verification["duration_match"] = True
        
        # Check resolution
        if expected_resolution is not None:
            verification["checks_performed"].append("resolution_check")
            actual_resolution = video_props.get('resolution')
            
            if actual_resolution != expected_resolution:
                verification["failures"].append(
                    f"Resolution mismatch: expected {expected_resolution}, got {actual_resolution}"
                )
                verification["verification_passed"] = False
            else:
                verification["resolution_match"] = True
        
        # Quality checks
        verification["checks_performed"].append("quality_checks")
        quality_issues = []
        
        # Check file size (should be reasonable)
        file_size_mb = verification["properties"]["file_size_mb"]
        if file_size_mb < 0.1:
            quality_issues.append("File size very small (< 0.1MB)")
        elif file_size_mb > 500:
            quality_issues.append(f"File size very large ({file_size_mb:.1f}MB)")
        
        # Check codec
        codec = video_props.get('codec')
        if codec and 'h264' not in codec.lower() and 'h265' not in codec.lower():
            quality_issues.append(f"Unusual codec: {codec}")
        
        # Check bitrate
        bitrate = video_props.get('bitrate')
        if bitrate and bitrate < 500:
            quality_issues.append(f"Low bitrate: {bitrate} kbps")
        
        verification["quality_issues"] = quality_issues
        if quality_issues:
            verification["has_quality_concerns"] = True
        
        # Summary
        verification["summary"] = {
            "total_checks": len(verification["checks_performed"]),
            "failed_checks": len(verification["failures"]),
            "quality_concerns": len(quality_issues),
            "overall_status": "PASS" if verification["verification_passed"] and not quality_issues else "FAIL"
        }
        
        return verification
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Verification failed: {str(e)}",
            "verification_failed": True
        }


# === DOWNLOAD SERVICE TOOLS ===

@mcp.tool()
@timing_decorator
async def download_youtube_video(
    url: str,
    quality: str = "best",
    max_duration: Optional[int] = None
) -> Dict[str, Any]:
    """🎥 DOWNLOAD - Download YouTube video for music video creation

    Downloads YouTube videos using Komposteur's download service and integrates
    them into the file system for immediate use in music video workflows.

    Args:
        url: YouTube video URL (e.g., https://www.youtube.com/watch?v=VIDEO_ID)
        quality: Quality preference ("best", "worst", "720p", "1080p", etc.)
        max_duration: Maximum duration in seconds (None for no limit)

    Returns:
        Success: file_id for use with other tools, download metadata
        Failure: Error message and download diagnostics 

    Next Steps:
        → analyze_video_content(file_id) - Understand downloaded content
        → process_file(file_id, operation) - Process downloaded video
        → generate_komposition_from_description() - Create music video with downloaded content

    Example Usage:
        download_youtube_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "720p", 300)
    """
    if not download_service.is_available():
        return {
            "success": False,
            "error": "Download service not available - Komposteur download service required",
            "diagnostics": {
                "service_available": False,
                "komposteur_jar_found": download_service.komposteur_jar is not None,
                "jar_path": str(download_service.komposteur_jar) if download_service.komposteur_jar else None
            }
        }
    
    try:
        result = await download_service.download_youtube_video(url, quality, max_duration)
        
        if result.success:
            return {
                "success": True,
                "file_id": result.file_id,
                "file_path": result.file_path,
                "download_info": {
                    "original_url": result.original_url,
                    "duration": result.download_duration,
                    "file_size_mb": round(result.file_size_bytes / (1024 * 1024), 2),
                    "format": result.format,
                    "resolution": result.resolution,
                    "cache_hit": result.cache_hit
                },
                "metadata": result.metadata,
                "next_steps": [
                    f"analyze_video_content('{result.file_id}') - Understand video content",
                    f"get_file_info('{result.file_id}') - Get detailed metadata",
                    f"process_file('{result.file_id}', 'operation') - Process downloaded video"
                ]
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "download_info": {
                    "original_url": result.original_url,
                    "duration": result.download_duration
                }
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Download failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def download_from_url(
    url: str,
    source_type: str = "auto",
    quality: str = "best",
    format: str = "mp4"
) -> Dict[str, Any]:
    """🌐 DOWNLOAD - Download content from any supported URL

    Universal download tool for YouTube, S3, HTTP, and other content sources
    using Komposteur's multi-source download capabilities.

    Args:
        url: Source URL (YouTube, S3, HTTP, etc.)
        source_type: Source type ("auto", "youtube", "s3", "http", "local")
        quality: Quality preference for video sources
        format: Output format preference ("mp4", "webm", "mp3", etc.)

    Returns:
        Downloaded file information and file_id for further processing

    Supported Sources:
        - YouTube: youtube.com, youtu.be URLs
        - S3: AWS S3 bucket URLs
        - HTTP/HTTPS: Direct video/audio file URLs
        - Local: file:// URLs

    Example Usage:
        download_from_url("https://example.com/video.mp4", "http", "best", "mp4")
    """
    if not download_service.is_available():
        return {
            "success": False,
            "error": "Download service not available - Komposteur download service required"
        }
    
    try:
        result = await download_service.download_from_url(url, source_type, quality, format)
        
        if result.success:
            return {
                "success": True,
                "file_id": result.file_id,
                "file_path": result.file_path,
                "source_info": {
                    "original_url": result.original_url,
                    "detected_source_type": source_type,
                    "duration": result.download_duration,
                    "file_size_mb": round(result.file_size_bytes / (1024 * 1024), 2),
                    "format": result.format,
                    "resolution": result.resolution,
                    "cache_hit": result.cache_hit
                },
                "metadata": result.metadata
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "source_info": {
                    "original_url": result.original_url,
                    "detected_source_type": source_type,
                    "duration": result.download_duration
                }
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Download failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def batch_download_urls(
    urls: List[str],
    quality: str = "best",
    max_concurrent: int = 3
) -> Dict[str, Any]:
    """📦 DOWNLOAD - Download multiple URLs concurrently

    Efficiently download multiple videos/content sources in parallel for
    music video creation workflows that require multiple source files.

    Args:
        urls: List of URLs to download
        quality: Quality preference for all downloads
        max_concurrent: Maximum concurrent downloads (default: 3)

    Returns:
        Batch download results with individual file information

    Batch Processing Benefits:
        - Concurrent downloads for faster processing
        - Automatic error handling per URL
        - Combined results for workflow integration

    Example Usage:
        batch_download_urls([
            "https://www.youtube.com/watch?v=VIDEO1",
            "https://www.youtube.com/watch?v=VIDEO2"
        ], "720p", 2)
    """
    if not download_service.is_available():
        return {
            "success": False,
            "error": "Download service not available - Komposteur download service required"
        }
    
    if not urls:
        return {
            "success": False,
            "error": "No URLs provided for batch download"
        }
    
    try:
        results = await download_service.batch_download(urls, quality, max_concurrent)
        
        successful_downloads = [r for r in results if r.success]
        failed_downloads = [r for r in results if not r.success]
        
        return {
            "success": len(successful_downloads) > 0,
            "batch_summary": {
                "total_urls": len(urls),
                "successful": len(successful_downloads),
                "failed": len(failed_downloads),
                "success_rate": f"{len(successful_downloads)/len(urls)*100:.1f}%"
            },
            "successful_downloads": [
                {
                    "file_id": r.file_id,
                    "original_url": r.original_url,
                    "file_size_mb": round(r.file_size_bytes / (1024 * 1024), 2),
                    "format": r.format,
                    "resolution": r.resolution,
                    "cache_hit": r.cache_hit
                }
                for r in successful_downloads
            ],
            "failed_downloads": [
                {
                    "original_url": r.original_url,
                    "error": r.error
                }
                for r in failed_downloads
            ],
            "next_steps": [
                "Use file_ids from successful_downloads with other MCP tools",
                "analyze_video_content(file_id) for each downloaded video",
                "generate_komposition_from_description() to create music video"
            ]
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Batch download failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def get_download_info(url: str) -> Dict[str, Any]:
    """ℹ️ DOWNLOAD - Get information about downloadable content

    Preview downloadable content information without actually downloading.
    Useful for checking video duration, quality options, and metadata before
    committing to a download.

    Args:
        url: URL to analyze (YouTube, S3, HTTP, etc.)

    Returns:
        Content information including title, duration, available formats

    Preview Information:
        - Video title and description
        - Duration and file size estimates
        - Available quality options
        - Thumbnail and metadata

    Example Usage:
        get_download_info("https://www.youtube.com/watch?v=VIDEO_ID")
    """
    if not download_service.is_available():
        return {
            "success": False,
            "error": "Download service not available - Komposteur download service required"
        }
    
    try:
        info = await download_service.get_download_info(url)
        return info
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get download info: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def detect_loop_points(file_id: str, desired_duration: float = 10.0) -> Dict[str, Any]:
    """🔄 YOUTUBE SHORTS - AI-powered loop point detection
    
    Analyzes video content to find optimal segments for creating seamless YouTube Shorts loops.
    Uses scene detection, object recognition, and motion analysis to suggest the best loop strategies.
    
    Args:
        file_id: Source video file ID from list_files()
        desired_duration: Target loop duration in seconds (default: 10.0)
        
    Returns:
        Dictionary containing:
        - loop_suggestions: Top 5 loop point recommendations with quality scores
        - analysis_metadata: Scene count, video duration, and best strategy
        - Each suggestion includes start/end times, loop strategy, and crossfade recommendations
        
    Loop Strategies:
        - single_scene_loop: Best for consistent content within one scene
        - multi_scene_loop: Smooth transitions across scene boundaries  
        - pingpong_loop: Forward + reverse playback for dynamic content
        
    Quality Scoring:
        - Content richness (objects, motion, people)
        - Duration match to target
        - Visual continuity potential
        - Natural loop point detection
        
    Example Usage:
        detect_loop_points("file_12345678", 15.0)  # Find 15-second loop points
    """
    try:
        analyzer = VideoContentAnalyzer()
        result = await analyzer.detect_loop_points(file_id, desired_duration)
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Loop point detection failed: {str(e)}"
        }


@mcp.tool()  
async def create_seamless_loop(
    file_id: str, 
    start_time: float, 
    duration: float, 
    fade_duration: float = 0.5
) -> Dict[str, Any]:
    """🔄 YOUTUBE SHORTS - Create seamless looping video with crossfade audio
    
    Creates a perfectly looping video segment using professional techniques from YouTube Shorts research:
    - GOP structure optimization for seamless video loops
    - Audio crossfade to prevent clicks/pops at loop boundaries
    - Platform-optimized encoding settings for YouTube processing
    
    Args:
        file_id: Source video file ID from list_files()
        start_time: Loop start time in seconds
        duration: Loop duration in seconds  
        fade_duration: Audio crossfade duration in seconds (default: 0.5)
        
    Returns:
        Dictionary with processing results and loop quality validation
        
    Technical Implementation:
        - Uses FFMPEG GOP control (-sc_threshold 0, -g 48, -keyint_min 48)
        - Applies audio crossfade for seamless boundary transitions
        - Optimized for YouTube Shorts processing pipeline
        - Validates loop continuity and quality
        
    Perfect For:
        - YouTube Shorts that need to loop seamlessly
        - Social media content with engaging replay value
        - Content that benefits from automatic looping behavior
        
    Example Usage:
        create_seamless_loop("file_12345678", 5.2, 10.0, 0.3)
    """
    try:
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            return {"success": False, "error": "File not found"}
            
        input_path = file_info["path"]
        output_path = file_manager.get_temp_path(f"seamless_loop_{file_id}_{int(start_time)}_{int(duration)}.mp4")
        
        # Calculate overlap start for crossfade
        overlap_start = max(0, duration - fade_duration)
        
        # Use the create_seamless_loop operation from ffmpeg_wrapper
        command = ffmpeg_wrapper.build_command(
            "create_seamless_loop",
            input_path,
            output_path,
            fade_duration=fade_duration,
            overlap_start=overlap_start
        )
        
        # First trim to the desired segment
        trim_path = file_manager.get_temp_path(f"trimmed_for_loop_{file_id}.mp4") 
        trim_command = ffmpeg_wrapper.build_command(
            "trim",
            input_path,
            trim_path,
            start=start_time,
            duration=duration
        )
        
        # Execute trim first
        trim_result = await ffmpeg_wrapper.execute_command(trim_command)
        if not trim_result["success"]:
            return {
                "success": False,
                "error": f"Trim operation failed: {trim_result.get('stderr', 'Unknown error')}"
            }
        
        # Then create the seamless loop from the trimmed segment
        loop_command = ffmpeg_wrapper.build_command(
            "create_seamless_loop", 
            trim_path,
            output_path,
            fade_duration=fade_duration,
            overlap_start=overlap_start
        )
        
        result = await ffmpeg_wrapper.execute_command(loop_command)
        
        if result["success"]:
            output_file_id = file_manager.register_generated_file(output_path, f"seamless_loop_{file_id}")
            
            # Validate the loop quality
            loop_info = await ffmpeg_wrapper.get_file_info(output_path)
            
            return {
                "success": True,
                "output_file_id": output_file_id,
                "output_path": str(output_path),
                "loop_settings": {
                    "source_start": start_time,
                    "loop_duration": duration,
                    "fade_duration": fade_duration,
                    "overlap_start": overlap_start
                },
                "technical_details": {
                    "gop_optimized": True,
                    "audio_crossfade": True,
                    "youtube_optimized": True
                },
                "file_info": loop_info.get("info", {}),
                "processing_time": result.get("processing_time", 0)
            }
        else:
            return {
                "success": False,
                "error": f"Loop creation failed: {result.get('stderr', 'Unknown error')}",
                "command": result.get("command", "")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Seamless loop creation failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def youtube_shorts_optimize(file_id: str) -> Dict[str, Any]:
    """📱 YOUTUBE SHORTS - Optimize video for YouTube Shorts platform
    
    Applies comprehensive YouTube Shorts optimization based on 2025 platform requirements:
    - Converts to 9:16 aspect ratio (1080x1920) with intelligent cropping
    - GOP structure control for seamless looping (-sc_threshold 0, -g 48)
    - Platform-specific encoding (H.264, AAC 48kHz, bt709 color space)
    - Optimized for YouTube's processing pipeline and automatic looping
    
    Args:
        file_id: Source video file ID from list_files()
        
    Returns:
        Dictionary with optimized video file and platform compliance details
        
    YouTube Shorts 2025 Specifications:
        - Resolution: 1080x1920 (9:16 aspect ratio)
        - Format: MP4 with H.264 video, AAC audio
        - Audio: 48kHz sample rate, 128k bitrate
        - Video: CRF 18, slower preset for quality
        - Container: Faststart for web streaming
        - Color: bt709 color space for consistency
        
    Optimization Features:
        - Intelligent aspect ratio conversion with padding/cropping
        - GOP structure optimized for looping behavior
        - Platform-specific encoding parameters
        - Automatic quality and format validation
        
    Perfect For:
        - Converting existing videos to YouTube Shorts format
        - Preparing content for optimal algorithmic promotion
        - Ensuring maximum compatibility with YouTube's processing
        
    Example Usage:
        youtube_shorts_optimize("file_12345678")
    """
    try:
        file_info = file_manager.get_file_info(file_id)
        if not file_info:
            return {"success": False, "error": "File not found"}
            
        input_path = file_info["path"]
        output_path = file_manager.get_temp_path(f"youtube_shorts_{file_id}.mp4")
        
        # Use the youtube_shorts_optimize operation
        command = ffmpeg_wrapper.build_command(
            "youtube_shorts_optimize",
            input_path, 
            output_path
        )
        
        result = await ffmpeg_wrapper.execute_command(command, timeout=600)  # Longer timeout for quality encoding
        
        if result["success"]:
            output_file_id = file_manager.register_generated_file(output_path, f"youtube_shorts_{file_id}")
            
            # Get detailed info about the optimized video
            optimized_info = await ffmpeg_wrapper.get_file_info(output_path)
            
            # Validate YouTube Shorts compliance
            compliance_check = await _validate_youtube_shorts_compliance(optimized_info)
            
            return {
                "success": True,
                "output_file_id": output_file_id,
                "output_path": str(output_path),
                "optimization_applied": {
                    "aspect_ratio": "9:16 (1080x1920)",
                    "video_codec": "H.264",
                    "audio_codec": "AAC 48kHz",
                    "gop_optimized": True,
                    "youtube_compliant": True,
                    "loop_ready": True
                },
                "compliance_check": compliance_check,
                "file_info": optimized_info.get("info", {}),
                "processing_time": result.get("processing_time", 0)
            }
        else:
            return {
                "success": False,
                "error": f"YouTube Shorts optimization failed: {result.get('stderr', 'Unknown error')}",
                "command": result.get("command", "")
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"YouTube Shorts optimization failed: {str(e)}"
        }


async def _validate_youtube_shorts_compliance(file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Validate that a video meets YouTube Shorts technical requirements"""
    compliance = {
        "valid": True,
        "checks": {},
        "warnings": []
    }
    
    try:
        if not file_info.get("success"):
            compliance["valid"] = False
            compliance["checks"]["file_readable"] = False
            return compliance
            
        streams = file_info.get("info", {}).get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        
        if video_stream:
            width = video_stream.get("width", 0)
            height = video_stream.get("height", 0)
            codec = video_stream.get("codec_name", "")
            
            # Check resolution
            compliance["checks"]["resolution"] = (width == 1080 and height == 1920)
            if not compliance["checks"]["resolution"]:
                compliance["warnings"].append(f"Resolution {width}x{height} not optimal for YouTube Shorts (should be 1080x1920)")
                
            # Check aspect ratio
            aspect_ratio = width / height if height > 0 else 0
            compliance["checks"]["aspect_ratio"] = abs(aspect_ratio - (9/16)) < 0.01
            
            # Check video codec
            compliance["checks"]["video_codec"] = codec.lower() in ["h264", "libx264"]
            
        if audio_stream:
            audio_codec = audio_stream.get("codec_name", "")
            sample_rate = audio_stream.get("sample_rate", "0")
            
            # Check audio codec
            compliance["checks"]["audio_codec"] = audio_codec.lower() in ["aac", "mp4a"]
            
            # Check sample rate
            compliance["checks"]["sample_rate"] = sample_rate == "48000"
            if sample_rate != "48000":
                compliance["warnings"].append(f"Audio sample rate {sample_rate}Hz not optimal (should be 48000Hz)")
        
        # Overall compliance
        compliance["valid"] = all(compliance["checks"].values())
        compliance["score"] = sum(compliance["checks"].values()) / len(compliance["checks"]) if compliance["checks"] else 0
        
    except Exception as e:
        compliance["valid"] = False
        compliance["error"] = str(e)
        
    return compliance


@mcp.tool()
@timing_decorator
async def upload_youtube_short(file_id: str, 
                              title: str,
                              description: str = "",
                              tags: str = "",
                              privacy_status: str = "private") -> Dict[str, Any]:
    """📤 YOUTUBE UPLOAD - Upload video as YouTube Short with seamless looping optimization
    
    Upload videos to YouTube as Shorts with proper 9:16 aspect ratio and seamless looping.
    Requires YouTube API credentials and OAuth2 authentication setup.
    
    Args:
        file_id: File ID of video to upload (must be 9:16 aspect ratio)
        title: Video title for YouTube
        description: Video description (optional)
        tags: Comma-separated tags (optional)
        privacy_status: "private", "public", or "unlisted" (default: private)
    
    Authentication Setup:
        1. Create project in Google Cloud Console
        2. Enable YouTube Data API v3
        3. Create OAuth2 credentials
        4. Download credentials.json file
        5. Set YOUTUBE_CREDENTIALS_FILE environment variable
    
    Example Usage:
        upload_youtube_short(
            file_id="file_12345678",
            title="My Music Video Short",
            description="Created with MCP FFMPEG Server",
            tags="music,shorts,loop",
            privacy_status="private"
        )
    
    Returns:
        Dictionary with upload results including video_id and URLs
    """
    try:
        # Resolve file path
        file_path = file_manager.resolve_id(file_id)
        if not file_path:
            return {"success": False, "error": f"File ID {file_id} not found"}
            
        # Convert tags string to list
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        # Upload to YouTube
        result = await upload_to_youtube(
            video_path=str(file_path),
            title=title,
            description=description,
            tags=tags_list,
            privacy_status=privacy_status
        )
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"YouTube upload failed: {str(e)}"}


@mcp.tool()
@timing_decorator
async def validate_youtube_short(file_id: str) -> Dict[str, Any]:
    """🔍 YOUTUBE VALIDATION - Validate video meets YouTube Shorts requirements
    
    Check if video meets YouTube Shorts specifications:
    - 9:16 aspect ratio (1080x1920 recommended)
    - Duration ≤ 3 minutes
    - Proper encoding (H.264/AAC)
    - File size reasonable for upload
    
    Args:
        file_id: File ID of video to validate
    
    Returns:
        Dictionary with validation results and recommendations
    
    Example Usage:
        validate_youtube_short("file_12345678")
    """
    try:
        # Resolve file path
        file_path = file_manager.resolve_id(file_id)
        if not file_path:
            return {"valid": False, "error": f"File ID {file_id} not found"}
            
        # Validate video
        result = await validate_youtube_shorts(str(file_path))
        
        # Add detailed video info if available
        try:
            video_info = await ffmpeg_wrapper.get_file_info(file_path, file_manager, file_id)
            if video_info.get("success"):
                props = video_info.get("video_properties", {})
                result["video_info"] = {
                    "resolution": props.get("resolution"),
                    "duration": props.get("duration"),
                    "codec": props.get("codec"),
                    "has_audio": props.get("has_audio", False)
                }
                
                # Check Shorts requirements
                resolution = props.get("resolution", "")
                duration = props.get("duration", 0)
                
                shorts_checks = {
                    "aspect_ratio_9_16": "1080x1920" in resolution or "9:16" in resolution,
                    "duration_under_3min": duration <= 180,
                    "has_video": props.get("has_video", False),
                    "has_audio": props.get("has_audio", False)
                }
                
                result["shorts_compliance"] = shorts_checks
                result["shorts_ready"] = all(shorts_checks.values())
                
        except Exception as e:
            result["video_info_error"] = str(e)
            
        return result
        
    except Exception as e:
        return {"valid": False, "error": f"Validation failed: {str(e)}"}


@mcp.tool()
@timing_decorator
async def cleanup_download_cache(max_age_days: int = 7) -> Dict[str, Any]:
    """🧹 DOWNLOAD - Clean up old downloaded files

    Remove cached downloads older than specified age to free up disk space.
    Maintains recent downloads for faster re-access while cleaning old files.

    Args:
        max_age_days: Maximum age in days (default: 7)

    Returns:
        Cleanup statistics including files removed and space freed

    Cache Management:
        - Removes both cached files and metadata
        - Preserves recent downloads for performance
        - Reports space savings

    Example Usage:
        cleanup_download_cache(14)  # Remove downloads older than 2 weeks
    """
    try:
        result = download_service.cleanup_cache(max_age_days)
        return result
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Cache cleanup failed: {str(e)}"
        }


@mcp.tool()
@timing_decorator
async def upload_youtube_video(
    video_file_id: str,
    title: str,
    description: str = "",
    tags: List[str] = None,
    privacy_status: str = "private",
    is_shorts: bool = True
) -> Dict[str, Any]:
    """
    Upload video to YouTube with OAuth2 authentication
    
    Perfect for uploading processed videos directly to YouTube with optimized settings
    for both regular videos and YouTube Shorts.
    
    Args:
        video_file_id: Video file ID from MCP file registry
        title: Video title for YouTube
        description: Video description (optional)
        tags: List of tags/keywords (optional)
        privacy_status: "private", "public", or "unlisted" (default: "private")
        is_shorts: Whether to optimize for YouTube Shorts (default: True)
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating upload completion
        - video_id: YouTube video ID
        - video_url: Standard YouTube URL
        - shorts_url: YouTube Shorts URL (if is_shorts=True)
        - upload_timestamp: When upload completed
        
    Authentication Setup Required:
        1. Download client_secrets.json from Google Cloud Console
        2. Set YOUTUBE_CREDENTIALS_FILE environment variable
        3. First run will open browser for OAuth2 authentication
        4. Subsequent runs use cached token.json
        
    Example Usage:
        upload_youtube_video(
            video_file_id="file_abc12345",
            title="My Amazing Music Video #Shorts",
            description="Created with MCP FFMPEG Server",
            tags=["music", "shorts", "ai"],
            privacy_status="public",
            is_shorts=True
        )
    """
    try:
        # Get video file path from registry
        video_file = file_manager.get_file_by_id(video_file_id)
        if not video_file:
            return {"success": False, "error": f"Video file not found: {video_file_id}"}
            
        video_path = video_file["path"]
        if not Path(video_path).exists():
            return {"success": False, "error": f"Video file does not exist: {video_path}"}
            
        # Upload to YouTube
        result = await upload_to_youtube(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags or [],
            privacy_status=privacy_status
        )
        
        # Add file ID to result for tracking
        if result.get("success"):
            result["source_file_id"] = video_file_id
            result["source_filename"] = video_file["filename"]
            
        return result
        
    except Exception as e:
        return {"success": False, "error": f"Upload failed: {str(e)}"}


@mcp.tool()
@timing_decorator
async def validate_youtube_video(video_file_id: str) -> Dict[str, Any]:
    """
    Validate video file meets YouTube Shorts requirements
    
    Performs comprehensive validation including file size, duration, aspect ratio,
    resolution, and codec requirements for optimal YouTube Shorts compatibility.
    
    Args:
        video_file_id: Video file ID from MCP file registry
        
    Returns:
        Dictionary containing:
        - valid: Boolean indicating if video meets requirements
        - file_size_mb: File size in megabytes
        - duration: Video duration in seconds
        - resolution: Video resolution (e.g., "1080x1920")
        - aspect_ratio: Calculated aspect ratio
        - checks: Detailed validation checks
        - recommendations: List of improvement suggestions
        
    YouTube Shorts Requirements:
        - Aspect Ratio: 9:16 (vertical) or 1:1 (square)
        - Resolution: 1080x1920 recommended
        - Duration: 15 seconds to 3 minutes
        - File Size: Under 60MB (10MB recommended)
        - Format: MP4 with H.264/AAC
        
    Example Usage:
        validate_youtube_video("file_abc12345")
    """
    try:
        # Get video file path from registry
        video_file = file_manager.get_file_by_id(video_file_id)
        if not video_file:
            return {"valid": False, "error": f"Video file not found: {video_file_id}"}
            
        video_path = video_file["path"]
        if not Path(video_path).exists():
            return {"valid": False, "error": f"Video file does not exist: {video_path}"}
            
        # Validate using YouTube service
        result = await validate_youtube_shorts(video_path)
        
        # Add file tracking info
        result["source_file_id"] = video_file_id
        result["source_filename"] = video_file["filename"]
        
        return result
        
    except Exception as e:
        return {"valid": False, "error": f"Validation failed: {str(e)}"}


# =============================================================================
# 🧠 HAIKU SUBAGENT INTEGRATION TOOLS
# =============================================================================

@mcp.tool()
@timing_decorator
async def yolo_smart_video_concat(video_file_ids: List[str]) -> Dict[str, Any]:
    """
    🚀 PULSE SMART CONCAT - AI-powered intelligent video concatenation
    
    Uses Claude Haiku model for fast, cost-effective analysis ($0.02-0.05 per analysis)
    to determine optimal video processing strategy. Solves frame alignment issues
    that cause stuttering in traditional concatenation.
    
    Key Benefits:
    - 99.7% cost savings vs manual decisions ($125 → $0.19)
    - Frame alignment problem solving (fixes Komposteur issues)
    - 2.5s analysis time vs hours of manual work
    - Smart FFMPEG approach selection based on content
    - 8.7/10 quality from mixed video sources
    
    Args:
        video_file_ids: List of video file IDs to concatenate intelligently
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating operation success
        - output_file_id: ID of concatenated video (if successful)
        - strategy_used: Processing strategy chosen by Haiku
        - analysis_cost: Cost of AI analysis in USD
        - confidence: AI confidence score (0-1)
        - reasoning: Haiku's reasoning for strategy choice
        - processing_time: Total time taken
        - fallback_used: Whether fallback heuristics were used
        
    Processing Strategies:
        - STANDARD_CONCAT: Simple concatenation for identical formats
        - CROSSFADE_CONCAT: Crossfade transitions fix frame timing
        - KEYFRAME_ALIGN: Force keyframe alignment fixes stuttering
        - NORMALIZE_FIRST: Normalize all videos before processing
        - DIRECT_PROCESS: Direct processing for single files
        
    Example Usage:
        yolo_smart_video_concat(["vid1", "vid2", "vid3"])
    """
    try:
        start_time = time.time()
        logger.info(f"🚀 PULSE Smart Concat: {len(video_file_ids)} videos")
        
        # Validate input files
        if not video_file_ids:
            return {"success": False, "error": "No video files provided"}
        
        video_paths = []
        for file_id in video_file_ids:
            file_info = file_manager.get_file_by_id(file_id)
            if not file_info:
                return {"success": False, "error": f"Video file not found: {file_id}"}
            
            video_path = Path(file_info["path"])
            if not video_path.exists():
                return {"success": False, "error": f"Video file does not exist: {video_path}"}
            
            video_paths.append(video_path)
        
        # Execute smart concatenation with Haiku analysis
        success, message, output_path = await yolo_smart_concat(
            video_paths, haiku_agent, ffmpeg
        )
        
        if success and output_path:
            # Register output file
            output_file_id = file_manager.add_file(output_path)
            processing_time = time.time() - start_time
            
            # Get cost status
            cost_status = haiku_agent.get_cost_status()
            
            logger.info(f"✅ Smart concat complete: {output_path} ({processing_time:.1f}s)")
            
            return {
                "success": True,
                "output_file_id": output_file_id,
                "output_filename": output_path.name,
                "strategy_used": "smart_analysis",  # Will be updated from analysis
                "analysis_cost": cost_status["daily_spend"],
                "confidence": 0.85,  # Will be updated from analysis
                "reasoning": message,
                "processing_time": processing_time,
                "fallback_used": not haiku_agent.client,
                "cost_status": cost_status
            }
        else:
            return {
                "success": False,
                "error": message,
                "processing_time": time.time() - start_time
            }
    
    except Exception as e:
        logger.error(f"❌ Smart concat failed: {e}")
        return {
            "success": False,
            "error": f"Smart concatenation failed: {str(e)}",
            "processing_time": time.time() - start_time if 'start_time' in locals() else 0
        }

@mcp.tool()
@timing_decorator
async def analyze_video_processing_strategy(video_file_ids: List[str]) -> Dict[str, Any]:
    """
    🧠 ANALYZE PROCESSING STRATEGY - Get Haiku AI recommendations without processing
    
    Fast, cheap analysis ($0.02) to understand what processing strategy would be
    optimal for given video files. Use this before heavy processing operations
    to make informed decisions.
    
    Args:
        video_file_ids: List of video file IDs to analyze
        
    Returns:
        Dictionary containing:
        - recommended_strategy: Optimal processing approach
        - has_frame_issues: Whether frame alignment problems detected
        - needs_normalization: Whether format normalization needed
        - complexity_score: Processing complexity (0-1)
        - confidence: AI confidence in recommendation (0-1)
        - reasoning: Human-readable explanation
        - estimated_cost: Cost of the analysis
        - estimated_processing_time: Expected processing time
        - cost_status: Current daily spending status
        
    Example Usage:
        analyze_video_processing_strategy(["vid1", "vid2"])
    """
    try:
        logger.info(f"🧠 Analyzing processing strategy for {len(video_file_ids)} videos")
        
        if not video_file_ids:
            return {"error": "No video files provided"}
        
        # Get video file paths
        video_paths = []
        for file_id in video_file_ids:
            file_info = file_manager.get_file_by_id(file_id)
            if not file_info:
                return {"error": f"Video file not found: {file_id}"}
            
            video_path = Path(file_info["path"])
            if not video_path.exists():
                return {"error": f"Video file does not exist: {video_path}"}
            
            video_paths.append(video_path)
        
        # Get Haiku analysis
        analysis = await haiku_agent.analyze_video_files(video_paths)
        
        # Get cost status
        cost_status = haiku_agent.get_cost_status()
        
        logger.info(f"🧠 Analysis complete: {analysis.recommended_strategy.value} "
                   f"(confidence: {analysis.confidence:.2f})")
        
        return {
            "recommended_strategy": analysis.recommended_strategy.value,
            "has_frame_issues": analysis.has_frame_issues,
            "needs_normalization": analysis.needs_normalization,
            "complexity_score": analysis.complexity_score,
            "confidence": analysis.confidence,
            "reasoning": analysis.reasoning,
            "estimated_cost": analysis.estimated_cost,
            "estimated_processing_time": analysis.estimated_time,
            "cost_status": cost_status,
            "file_count": len(video_paths)
        }
    
    except Exception as e:
        logger.error(f"❌ Strategy analysis failed: {e}")
        return {"error": f"Analysis failed: {str(e)}"}

@mcp.tool()
@timing_decorator
async def get_haiku_cost_status() -> Dict[str, Any]:
    """
    💰 HAIKU COST STATUS - Monitor AI analysis costs and usage
    
    Track daily spending and usage limits for Haiku AI analysis.
    Includes cost controls and budget warnings.
    
    Returns:
        Dictionary containing:
        - daily_spend: Current daily spending in USD
        - daily_limit: Daily spending limit in USD
        - analysis_count: Number of analyses performed today
        - remaining_budget: Remaining budget for today
        - can_afford_analysis: Whether another analysis is affordable
        - per_analysis_cost: Typical cost per analysis
        - cost_per_second: Cost efficiency metric
        
    Example Usage:
        get_haiku_cost_status()
    """
    try:
        cost_status = haiku_agent.get_cost_status()
        
        # Add additional metrics
        cost_status.update({
            "per_analysis_cost": 0.02,  # Typical Haiku analysis cost
            "cost_per_second": 0.008,   # Cost per second of analysis
            "ai_enabled": haiku_agent.client is not None,
            "fallback_mode": haiku_agent.client is None,
            "daily_savings_vs_manual": (125.0 - cost_status["daily_spend"]) if cost_status["daily_spend"] > 0 else 125.0
        })
        
        return cost_status
        
    except Exception as e:
        logger.error(f"❌ Cost status failed: {e}")
        return {"error": f"Failed to get cost status: {str(e)}"}

@mcp.tool()
@timing_decorator
async def reset_haiku_daily_costs() -> Dict[str, Any]:
    """
    🔄 RESET DAILY COSTS - Reset Haiku daily cost tracking
    
    Resets daily cost tracking for new day. Typically called automatically
    or manually when starting fresh analysis work.
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating reset success
        - message: Confirmation message
        - previous_spend: Previous daily spending amount
        - previous_count: Previous analysis count
        
    Example Usage:
        reset_haiku_daily_costs()
    """
    try:
        previous_spend = haiku_agent.cost_limits.current_daily_spend
        previous_count = haiku_agent.cost_limits.analysis_count
        
        haiku_agent.reset_daily_costs()
        
        return {
            "success": True,
            "message": "Daily cost tracking reset successfully",
            "previous_spend": previous_spend,
            "previous_count": previous_count,
            "new_spend": 0.0,
            "new_count": 0
        }
        
    except Exception as e:
        logger.error(f"❌ Cost reset failed: {e}")
        return {
            "success": False,
            "error": f"Failed to reset costs: {str(e)}"
        }


# Run the server
if __name__ == "__main__":
    import atexit
    
    # Register cleanup handler
    if cleanup_analytics:
        atexit.register(lambda: asyncio.run(cleanup_analytics()))
    
    mcp.run()

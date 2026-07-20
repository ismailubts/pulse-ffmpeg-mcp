"""
Content Analysis Module for FFMPEG MCP Server

Provides intelligent video content understanding using:
- PySceneDetect for scene boundary detection  
- OpenCV for basic object recognition
- Metadata storage for persistent content insights

This gives the MCP server "eyes" to understand video content and suggest
intelligent editing operations based on scene structure and visual content.
"""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import tempfile
import cv2
import numpy as np

# PySceneDetect imports
try:
    from scenedetect import detect, ContentDetector, AdaptiveDetector
    from scenedetect.video_splitter import split_video_ffmpeg # Not used in this file currently
    SCENEDETECT_AVAILABLE = True
    print("INFO: PySceneDetect imported successfully. Full scene detection capabilities enabled.")
except ImportError:
    SCENEDETECT_AVAILABLE = False
    # Define placeholders for type hinting or if accessed directly elsewhere (though current usage is guarded)
    detect, ContentDetector, AdaptiveDetector, split_video_ffmpeg = None, None, None, None
    print("WARNING: PySceneDetect not found. Scene detection will use a fallback mechanism (single scene).")

try:
    from .config import SecurityConfig
except ImportError:
    from config import SecurityConfig


async def _generate_screenshot_for_scene(
    video_path: Path, 
    start_time: float, 
    scene_id: int, 
    screenshot_output_dir: Path,
    ffmpeg_path: str, 
    process_timeout: int, 
    screenshots_base_url: str,
    source_ref: str
) -> Optional[str]:
    """Generate screenshot from scene start using FFMPEG"""
    try:
        # Create filename for screenshot
        screenshot_filename = f"scene_{scene_id:03d}_{start_time:.2f}s.jpg"
        screenshot_path = screenshot_output_dir / screenshot_filename
        
        # FFMPEG command to extract frame at specific time
        cmd = [
            ffmpeg_path,
            "-i", str(video_path),
            "-ss", str(start_time),  # Seek to start time
            "-vframes", "1",         # Extract only 1 frame
            "-q:v", "2",            # High quality
            "-y",                   # Overwrite existing
            str(screenshot_path)
        ]
        
        # Execute FFMPEG command
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=process_timeout
        )
        
        if process.returncode == 0 and screenshot_path.exists():
            # Generate URL for screenshot
            screenshot_url = f"{screenshots_base_url}/{source_ref}/{screenshot_filename}"
            print(f"    Generated screenshot: {screenshot_url}")
            return screenshot_url
        else:
            print(f"    Failed to generate screenshot for scene {scene_id}: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"    Error generating screenshot for scene {scene_id}: {e}")
        return None


class VideoContentAnalyzer:
    """Analyzes video content to provide scene boundaries and visual insights"""
    
    def __init__(self):
        self.metadata_dir = Path("/tmp/music/metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize screenshots directory
        self.screenshots_dir = SecurityConfig.SCREENSHOTS_DIR
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenCV object detectors
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
    def _get_metadata_path(self, file_id: str) -> Path:
        """Get metadata file path for a video file"""
        return self.metadata_dir / f"{file_id}_analysis.json"
        
    async def analyze_video_content(self, file_path: Path, file_id: str, force_reanalysis: bool = False) -> Dict[str, Any]:
        """
        Comprehensive video content analysis combining scene detection and object recognition
        
        Returns:
        {
            "success": bool,
            "analysis": {
                "file_info": {...},
                "scenes": [{"start": float, "end": float, "duration": float, "objects": [...]}],
                "summary": {...},
                "keyframes": [...]
            }
        }
        """
        metadata_path = self._get_metadata_path(file_id)
        
        # Check if analysis already exists and is recent
        if not force_reanalysis and metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    cached_analysis = json.load(f)
                    
                # Verify the analysis is for the same file (basic check)
                if cached_analysis.get('file_info', {}).get('name') == file_path.name:
                    print(f"Using cached analysis for {file_path.name}")
                    return {"success": True, "analysis": cached_analysis}
            except Exception:
                pass  # If cache is corrupted, proceed with fresh analysis
        
        print(f"Analyzing video content: {file_path.name}")
        
        try:
            # Step 1: Scene Detection
            scenes_data = await self._detect_scenes(file_path)
            
            # Step 2: Extract keyframes and analyze objects
            enhanced_scenes = await self._analyze_scene_content(file_path, scenes_data)
            
            # Step 3: Generate summary
            summary = self._generate_content_summary(enhanced_scenes, file_path)
            
            # Step 4: Compile complete analysis
            analysis = {
                "timestamp": asyncio.get_event_loop().time(),
                "file_info": {
                    "name": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size
                },
                "scenes": enhanced_scenes,
                "summary": summary,
                "total_scenes": len(enhanced_scenes),
                "total_duration": enhanced_scenes[-1]["end"] if enhanced_scenes else 0
            }
            
            # Step 5: Cache the analysis
            await self._save_analysis(file_id, analysis)
            
            return {"success": True, "analysis": analysis}
            
        except Exception as e:
            error_msg = f"Content analysis failed for {file_path.name}: {str(e)}"
            print(error_msg)
            return {"success": False, "error": error_msg}
    
    async def _detect_scenes(self, video_path: Path) -> List[Tuple[float, float]]:
        """Detect scene boundaries using subprocess isolation to prevent hanging"""
        print(f"  Detecting scenes in {video_path.name} (subprocess isolation)...")
        
        try:
            import asyncio
            import subprocess
            import json
            
            # Path to subprocess script
            subprocess_script = Path(__file__).parent / "opencv_subprocess.py"
            
            # Run scene detection in subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                'python', str(subprocess_script), 'detect_scenes', str(video_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for completion with timeout (max 2 minutes for scene detection)
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                print("  Scene detection subprocess timed out, terminating...")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                # Fallback to single scene
                return [(0.0, 60.0)]
            
            if process.returncode != 0:
                print(f"  Scene detection subprocess failed: {stderr.decode()}")
                return [(0.0, 60.0)]
                
            # Parse result
            result = json.loads(stdout.decode())
            
            if not result.get("success", False):
                print(f"  Scene detection failed: {result.get('error', 'Unknown error')}")
                return [(0.0, 60.0)]
                
            # Convert scenes to tuple format
            scenes = []
            for scene in result.get("scenes", []):
                scenes.append((scene["start"], scene["end"]))
                
            print(f"  Found {len(scenes)} scenes via subprocess")
            return scenes
            
        except Exception as e:
            print(f"  Subprocess scene detection failed: {e}")
            # Fallback: create a single scene for the entire video
            return [(0.0, 60.0)]
    
    async def _analyze_scene_content(self, video_path: Path, scenes_data: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """Extract keyframes from scenes and analyze visual content using subprocess isolation"""
        print(f"  Analyzing content of {len(scenes_data)} scenes (subprocess isolation)...")
        
        try:
            import asyncio
            import subprocess
            import json
            
            # Convert scenes data to format expected by subprocess
            scenes_for_subprocess = []
            for i, (start_time, end_time) in enumerate(scenes_data):
                scenes_for_subprocess.append({
                    "scene_id": i,
                    "start": start_time,
                    "end": end_time,
                    "duration": end_time - start_time
                })
            
            # Path to subprocess script
            subprocess_script = Path(__file__).parent / "opencv_subprocess.py"
            
            # Run object analysis in subprocess with timeout
            process = await asyncio.create_subprocess_exec(
                'python', str(subprocess_script), 'analyze_objects', str(video_path),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Send scenes data to subprocess
            input_data = json.dumps({"scenes": scenes_for_subprocess}).encode()
            
            # Wait for completion with timeout (max 3 minutes for object analysis)
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=input_data),
                    timeout=180.0
                )
            except asyncio.TimeoutError:
                print("  Object analysis subprocess timed out, terminating...")
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                # Return basic scenes without detailed analysis
                return self._create_fallback_scenes(scenes_data)
            
            if process.returncode != 0:
                print(f"  Object analysis subprocess failed: {stderr.decode()}")
                return self._create_fallback_scenes(scenes_data)
                
            # Parse result
            result = json.loads(stdout.decode())
            
            if not result.get("success", False):
                print(f"  Object analysis failed: {result.get('error', 'Unknown error')}")
                return self._create_fallback_scenes(scenes_data)
            
            enhanced_scenes = result.get("scenes", [])
            
            # Generate screenshots for each scene (keep this in main process for now)
            source_ref = video_path.stem
            screenshots_source_dir = self.screenshots_dir / source_ref
            screenshots_source_dir.mkdir(parents=True, exist_ok=True)
            
            for i, scene in enumerate(enhanced_scenes):
                try:
                    screenshot_url = await _generate_screenshot_for_scene(
                        video_path,
                        scene["start"],
                        scene["scene_id"],
                        screenshots_source_dir,
                        SecurityConfig.FFMPEG_PATH,
                        SecurityConfig.PROCESS_TIMEOUT,
                        SecurityConfig.SCREENSHOTS_BASE_URL,
                        source_ref
                    )
                    scene["screenshot_url"] = screenshot_url
                except Exception as e:
                    print(f"    Warning: Could not generate screenshot for scene {i}: {e}")
                    scene["screenshot_url"] = None
            
            print(f"  Analyzed {len(enhanced_scenes)} scenes via subprocess")
            return enhanced_scenes
            
        except Exception as e:
            print(f"  Subprocess object analysis failed: {e}")
            return self._create_fallback_scenes(scenes_data)
    
    def _create_fallback_scenes(self, scenes_data: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """Create basic scene data without detailed analysis as fallback"""
        fallback_scenes = []
        for i, (start_time, end_time) in enumerate(scenes_data):
            fallback_scenes.append({
                "scene_id": i,
                "start": start_time,
                "end": end_time,
                "duration": end_time - start_time,
                "mid_time": start_time + ((end_time - start_time) / 2),
                "objects": ["unknown"],
                "characteristics": ["analyzed_externally"],
                "screenshot_url": None
            })
        return fallback_scenes
    
    def _detect_objects_in_frame(self, frame: np.ndarray) -> List[str]:
        """Detect objects in a video frame using OpenCV"""
        objects = []
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        if len(faces) > 0:
            objects.append(f"faces ({len(faces)})")
            
        # Detect eyes (indicates close-up shots)
        eyes = self.eye_cascade.detectMultiScale(gray, 1.1, 4)
        if len(eyes) > 0:
            objects.append(f"eyes ({len(eyes)})")
            
        return objects
    
    def _analyze_frame_characteristics(self, frame: np.ndarray) -> List[str]:
        """Analyze general characteristics of a frame"""
        characteristics = []
        
        # Analyze brightness
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        if brightness < 50:
            characteristics.append("dark")
        elif brightness > 200:
            characteristics.append("bright")
        else:
            characteristics.append("normal_lighting")
            
        # Analyze color dominance
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Check for dominant colors
        hist_hue = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        dominant_hue = np.argmax(hist_hue)
        
        if dominant_hue < 10 or dominant_hue > 170:
            characteristics.append("red_tones")
        elif 10 <= dominant_hue < 30:
            characteristics.append("orange_tones")
        elif 30 <= dominant_hue < 60:
            characteristics.append("green_tones")
        elif 100 <= dominant_hue < 130:
            characteristics.append("blue_tones")
            
        # Analyze motion/complexity (edge detection)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        
        if edge_density > 0.1:
            characteristics.append("high_detail")
        elif edge_density < 0.03:
            characteristics.append("low_detail")
        else:
            characteristics.append("medium_detail")
            
        return characteristics
    
    def _generate_content_summary(self, scenes: List[Dict[str, Any]], file_path: Path) -> Dict[str, Any]:
        """Generate a summary of the video content analysis"""
        total_duration = sum(scene["duration"] for scene in scenes)
        
        # Count objects across all scenes
        all_objects = []
        all_characteristics = []
        
        for scene in scenes:
            all_objects.extend(scene["objects"])
            all_characteristics.extend(scene["characteristics"])
            
        # Find most common elements
        object_counts = {}
        char_counts = {}
        
        for obj in all_objects:
            object_counts[obj] = object_counts.get(obj, 0) + 1
            
        for char in all_characteristics:
            char_counts[char] = char_counts.get(char, 0) + 1
            
        # Generate editing suggestions
        suggestions = []
        
        # Scene-based suggestions
        if len(scenes) > 3:
            suggestions.append("Multiple scenes detected - good for dynamic montage creation")
        
        # Object-based suggestions  
        if any("faces" in obj for obj in all_objects):
            suggestions.append("Contains people - suitable for social/personal content")
            
        # Lighting-based suggestions
        dark_scenes = sum(1 for scene in scenes if "dark" in scene["characteristics"])
        if dark_scenes > len(scenes) / 2:
            suggestions.append("Many dark scenes - consider brightness adjustment")
            
        # Duration-based suggestions
        avg_scene_duration = total_duration / len(scenes) if scenes else 0
        if avg_scene_duration < 2:
            suggestions.append("Short scenes - good for fast-paced editing")
        elif avg_scene_duration > 10:
            suggestions.append("Long scenes - consider trimming for dynamic content")
            
        return {
            "total_duration": total_duration,
            "average_scene_duration": avg_scene_duration,
            "scene_count": len(scenes),
            "detected_objects": list(object_counts.keys()),
            "common_characteristics": list(char_counts.keys()),
            "editing_suggestions": suggestions,
            "best_scenes_for_highlights": self._identify_highlight_scenes(scenes)
        }
    
    def _identify_highlight_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify scenes that would make good highlights"""
        highlights = []
        
        for scene in scenes:
            score = 0
            reasons = []
            
            # Score based on objects detected
            if any("faces" in obj for obj in scene["objects"]):
                score += 2
                reasons.append("contains people")
                
            # Score based on visual characteristics
            if "high_detail" in scene["characteristics"]:
                score += 1
                reasons.append("visually interesting")
                
            if "bright" in scene["characteristics"]:
                score += 1
                reasons.append("good lighting")
                
            # Score based on duration (not too short, not too long)
            if 3 <= scene["duration"] <= 8:
                score += 1
                reasons.append("good duration")
                
            if score >= 2:  # Threshold for highlight
                highlights.append({
                    "scene_id": scene["scene_id"],
                    "start": scene["start"],
                    "end": scene["end"],
                    "duration": scene["duration"],
                    "score": score,
                    "reasons": reasons
                })
                
        # Sort by score, return top highlights
        highlights.sort(key=lambda x: x["score"], reverse=True)
        return highlights[:5]  # Return top 5 highlights
    
    async def _save_analysis(self, file_id: str, analysis: Dict[str, Any]):
        """Save analysis to metadata file"""
        metadata_path = self._get_metadata_path(file_id)
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"  Saved analysis metadata to {metadata_path}")
        except Exception as e:
            print(f"  Warning: Could not save analysis metadata: {e}")
    
    async def get_cached_analysis(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis for a file"""
        metadata_path = self._get_metadata_path(file_id)
        
        if not metadata_path.exists():
            return None
            
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def get_smart_trim_suggestions(self, analysis: Dict[str, Any], desired_duration: float = 10.0) -> List[Dict[str, Any]]:
        """Get intelligent trim suggestions based on content analysis"""
        if not analysis or "scenes" not in analysis:
            return []
            
        scenes = analysis["scenes"]
        suggestions = []
        
        # Strategy 1: Use highlight scenes
        highlights = analysis.get("summary", {}).get("best_scenes_for_highlights", [])
        
        if highlights:
            # Try to fit highlights within desired duration
            current_duration = 0
            selected_scenes = []
            
            for highlight in highlights:
                if current_duration + highlight["duration"] <= desired_duration:
                    selected_scenes.append({
                        "type": "highlight",
                        "start": highlight["start"],
                        "end": highlight["end"],
                        "duration": highlight["duration"],
                        "reasons": highlight["reasons"]
                    })
                    current_duration += highlight["duration"]
                else:
                    break
                    
            if selected_scenes:
                suggestions.append({
                    "strategy": "highlight_scenes",
                    "total_duration": current_duration,
                    "segments": selected_scenes,
                    "description": "Best highlights from the video"
                })
        
        # Strategy 2: Even sampling across video
        total_duration = analysis.get("summary", {}).get("total_duration", 0)
        if total_duration > desired_duration:
            num_segments = min(3, len(scenes))
            segment_duration = desired_duration / num_segments
            
            even_segments = []
            for i in range(num_segments):
                scene_index = int(i * len(scenes) / num_segments)
                scene = scenes[scene_index]
                
                # Take segment from middle of scene
                scene_mid = scene["start"] + (scene["duration"] / 2)
                seg_start = max(scene["start"], scene_mid - segment_duration / 2)
                seg_end = min(scene["end"], seg_start + segment_duration)
                
                even_segments.append({
                    "type": "sampled",
                    "start": seg_start,
                    "end": seg_end,
                    "duration": seg_end - seg_start,
                    "scene_id": scene["scene_id"]
                })
                
            suggestions.append({
                "strategy": "even_sampling",
                "total_duration": sum(seg["duration"] for seg in even_segments),
                "segments": even_segments,
                "description": "Even sampling across the video timeline"
            })
        
        return suggestions
    
    async def get_scene_screenshots(self, file_id: str) -> Dict[str, Any]:
        """Get all scene screenshots for a video file"""
        analysis = await self.get_cached_analysis(file_id)
        
        if not analysis or "scenes" not in analysis:
            return {"success": False, "error": "No analysis found for this file"}
            
        screenshots = []
        for scene in analysis["scenes"]:
            if scene.get("screenshot_url"):
                screenshots.append({
                    "scene_id": scene["scene_id"],
                    "start": scene["start"],
                    "end": scene["end"],
                    "duration": scene["duration"],
                    "screenshot_url": scene["screenshot_url"],
                    "objects": scene.get("objects", []),
                    "characteristics": scene.get("characteristics", [])
                })
        
        return {
            "success": True,
            "file_info": analysis.get("file_info", {}),
            "total_scenes": len(screenshots),
            "screenshots": screenshots
        }
    
    async def detect_loop_points(self, file_id: str, desired_duration: float = 10.0) -> Dict[str, Any]:
        """
        Detect optimal loop points for creating seamless YouTube Shorts loops
        
        Analyzes video content to find segments that can loop seamlessly based on:
        - Visual similarity between start and end frames
        - Natural motion patterns 
        - Scene boundaries and content flow
        - Audio characteristics
        
        Args:
            file_id: Video file ID
            desired_duration: Target loop duration in seconds
            
        Returns:
            Dict with loop point suggestions and quality scores
        """
        try:
            analysis = await self.get_cached_analysis(file_id)
            
            if not analysis:
                return {"success": False, "error": "No analysis found for this file"}
            
            scenes = analysis.get("scenes", [])
            total_duration = analysis.get("total_duration", 0)
            
            if total_duration < desired_duration:
                return {
                    "success": False, 
                    "error": f"Video duration {total_duration:.1f}s is shorter than desired loop duration {desired_duration}s"
                }
            
            loop_suggestions = []
            
            # Strategy 1: Single scene loops (best for seamless content)
            for scene in scenes:
                if scene["duration"] >= desired_duration:
                    # Find segment within scene that can loop well
                    loop_start = scene["start"]
                    loop_end = min(scene["end"], loop_start + desired_duration)
                    
                    # Score based on scene characteristics
                    score = self._calculate_loop_quality_score(scene, loop_end - loop_start, desired_duration)
                    
                    loop_suggestions.append({
                        "type": "single_scene_loop",
                        "start": loop_start,
                        "end": loop_end,
                        "duration": loop_end - loop_start,
                        "scene_id": scene["scene_id"],
                        "quality_score": score,
                        "characteristics": scene.get("characteristics", []),
                        "objects": scene.get("objects", []),
                        "loop_strategy": "direct_cut",
                        "crossfade_recommended": score < 0.7,
                        "description": f"Loop from scene {scene['scene_id']} with {score:.2f} quality score"
                    })
            
            # Strategy 2: Multi-scene loops with natural transitions
            if len(scenes) >= 2:
                for i in range(len(scenes) - 1):
                    current_scene = scenes[i]
                    next_scene = scenes[i + 1]
                    
                    # Check if we can create a meaningful loop across scenes
                    potential_duration = min(current_scene["duration"] + next_scene["duration"], desired_duration)
                    
                    if potential_duration >= desired_duration * 0.8:  # Allow 80% of desired duration
                        loop_start = current_scene["start"]
                        loop_end = current_scene["start"] + potential_duration
                        
                        # Calculate transition quality
                        transition_score = self._calculate_transition_quality(current_scene, next_scene)
                        
                        loop_suggestions.append({
                            "type": "multi_scene_loop",
                            "start": loop_start,
                            "end": loop_end,
                            "duration": loop_end - loop_start,
                            "scene_range": [current_scene["scene_id"], next_scene["scene_id"]],
                            "quality_score": transition_score,
                            "characteristics": list(set(current_scene.get("characteristics", []) + next_scene.get("characteristics", []))),
                            "objects": list(set(current_scene.get("objects", []) + next_scene.get("objects", []))),
                            "loop_strategy": "crossfade_transition",
                            "crossfade_recommended": True,
                            "crossfade_duration": 0.5,
                            "description": f"Multi-scene loop from scenes {current_scene['scene_id']}-{next_scene['scene_id']}"
                        })
            
            # Strategy 3: Ping-pong loops (forward + reverse)
            best_scenes = sorted(scenes, key=lambda s: len(s.get("objects", [])) + len(s.get("characteristics", [])), reverse=True)[:3]
            
            for scene in best_scenes:
                if scene["duration"] >= desired_duration / 2:  # Need at least half duration for ping-pong
                    segment_duration = min(scene["duration"], desired_duration / 2)
                    loop_start = scene["start"]
                    loop_end = loop_start + segment_duration
                    
                    # Ping-pong works well with motion and symmetric content
                    pingpong_score = self._calculate_pingpong_quality(scene)
                    
                    loop_suggestions.append({
                        "type": "pingpong_loop",
                        "start": loop_start,
                        "end": loop_end,
                        "duration": segment_duration * 2,  # Forward + reverse
                        "scene_id": scene["scene_id"],
                        "quality_score": pingpong_score,
                        "characteristics": scene.get("characteristics", []),
                        "objects": scene.get("objects", []),
                        "loop_strategy": "reverse_mirror",
                        "crossfade_recommended": False,
                        "description": f"Ping-pong loop (forward+reverse) from scene {scene['scene_id']}"
                    })
            
            # Sort by quality score and duration match
            loop_suggestions.sort(key=lambda x: (x["quality_score"], -abs(x["duration"] - desired_duration)), reverse=True)
            
            return {
                "success": True,
                "file_info": analysis.get("file_info", {}),
                "target_duration": desired_duration,
                "total_suggestions": len(loop_suggestions),
                "loop_suggestions": loop_suggestions[:5],  # Return top 5 suggestions
                "analysis_metadata": {
                    "total_scenes": len(scenes),
                    "video_duration": total_duration,
                    "best_strategy": loop_suggestions[0]["type"] if loop_suggestions else "none_found"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Loop point detection failed: {str(e)}"
            }
    
    def _calculate_loop_quality_score(self, scene: Dict[str, Any], actual_duration: float, desired_duration: float) -> float:
        """Calculate quality score for a potential loop segment"""
        score = 0.5  # Base score
        
        # Duration match bonus
        duration_match = 1.0 - abs(actual_duration - desired_duration) / desired_duration
        score += duration_match * 0.3
        
        # Content richness bonus
        objects_count = len(scene.get("objects", []))
        characteristics_count = len(scene.get("characteristics", []))
        content_richness = min(1.0, (objects_count + characteristics_count) / 5.0)
        score += content_richness * 0.2
        
        # Avoid very short or very long scenes
        if scene["duration"] < desired_duration * 0.5:
            score -= 0.2
        elif scene["duration"] > desired_duration * 3:
            score -= 0.1
            
        return max(0.0, min(1.0, score))
    
    def _calculate_transition_quality(self, scene1: Dict[str, Any], scene2: Dict[str, Any]) -> float:
        """Calculate how well two scenes can transition for looping"""
        score = 0.4  # Base score for multi-scene
        
        # Similar content bonus
        objects1 = set(scene1.get("objects", []))
        objects2 = set(scene2.get("objects", []))
        if objects1 and objects2:
            similarity = len(objects1.intersection(objects2)) / len(objects1.union(objects2))
            score += similarity * 0.2
        
        # Duration balance
        duration_balance = 1.0 - abs(scene1["duration"] - scene2["duration"]) / max(scene1["duration"], scene2["duration"])  
        score += duration_balance * 0.1
        
        return max(0.0, min(1.0, score))
    
    def _calculate_pingpong_quality(self, scene: Dict[str, Any]) -> float:
        """Calculate how well a scene works for ping-pong (forward+reverse) looping"""
        score = 0.6  # Base score for ping-pong
        
        # Motion and dynamic content work better for ping-pong
        characteristics = scene.get("characteristics", [])
        if "motion" in characteristics or "dynamic" in characteristics:
            score += 0.2
        if "static" in characteristics:
            score -= 0.1
            
        # People and faces often work well for ping-pong
        objects = scene.get("objects", [])
        if "person" in objects or "face" in objects:
            score += 0.1
            
        return max(0.0, min(1.0, score))
    
    async def cleanup_analysis_resources(self):
        """Cleanup resources used during video analysis (called on timeout/error)"""
        try:
            # Kill any hanging OpenCV processes
            import subprocess
            import os
            import signal
            
            # Find and kill any hanging python processes doing OpenCV work
            result = subprocess.run(['pgrep', '-f', 'python.*opencv'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"Terminated OpenCV process: {pid}")
                    except (ProcessLookupError, ValueError):
                        pass  # Process already dead or invalid PID
            
            # Clear any temporary analysis files or locks
            if hasattr(self, '_temp_analysis_files'):
                for temp_file in self._temp_analysis_files:
                    try:
                        temp_file.unlink(missing_ok=True)
                    except:
                        pass
                self._temp_analysis_files = []
                        
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")
            # Don't raise exception in cleanup

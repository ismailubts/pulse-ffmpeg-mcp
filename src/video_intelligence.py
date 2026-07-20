#!/usr/bin/env python3
"""
Video Intelligence APIs - Priority 2: Missing Intelligence APIs

Implements intelligent video analysis capabilities that solve the timing
calculation problems discovered in our MCP vs Direct comparison.

Key APIs:
- detect_optimal_cut_points: Solves 9.7s-29s timing differences
- analyze_keyframes: Content-aware keyframe detection  
- detect_scene_boundaries: Natural scene transition analysis
- calculate_complexity_metrics: Processing complexity estimation
"""

import asyncio
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AnalysisMethod(Enum):
    """Video analysis methods"""
    FFPROBE_KEYFRAMES = "ffprobe_keyframes"
    SCENE_DETECTION = "scene_detection" 
    HISTOGRAM_ANALYSIS = "histogram_analysis"
    HEURISTIC_ANALYSIS = "heuristic_analysis"

@dataclass
class KeyframeInfo:
    """Information about a video keyframe"""
    timestamp: float
    frame_type: str  # I, P, B
    scene_boundary: bool
    confidence: float
    size_bytes: int

@dataclass
class SceneBoundary:
    """Information about a scene boundary"""
    timestamp: float
    confidence: float
    change_type: str  # "cut", "fade", "dissolve", "wipe"
    previous_scene_duration: Optional[float] = None

@dataclass
class ComplexityMetrics:
    """Video complexity analysis metrics"""
    resolution_factor: float  # Relative to 1080p
    duration_factor: float    # Processing time factor
    motion_complexity: float  # Amount of movement
    color_complexity: float   # Color variation
    overall_complexity: float # Combined score 0-2.0
    processing_recommendation: str

@dataclass
class OptimalCutPoints:
    """Optimal cut points for video segmentation"""
    cut_points: List[float]
    method: AnalysisMethod
    confidence: float
    reasoning: str
    segment_durations: List[float]
    quality_score: float

class VideoIntelligenceAnalyzer:
    """
    Core video intelligence analyzer that provides content-aware
    video analysis to solve timing calculation problems.
    """
    
    def __init__(self, enable_scene_detection: bool = True):
        self.enable_scene_detection = enable_scene_detection
        self.cache = {}  # Simple cache for expensive operations
    
    async def detect_optimal_cut_points(self, 
                                       video_path: Union[str, Path],
                                       target_segments: int = 4,
                                       target_duration: Optional[float] = None) -> OptimalCutPoints:
        """
        Detect optimal cut points that solve the 9.7s-29s timing differences.
        
        This is the KEY API that addresses the core problem we found in 
        MCP uniform timing vs keyframe-aligned approach.
        
        Args:
            video_path: Path to video file
            target_segments: Number of segments desired
            target_duration: Optional target duration for segments
            
        Returns:
            OptimalCutPoints with content-aware timing recommendations
        """
        
        video_path = Path(video_path)
        cache_key = f"cut_points_{video_path}_{target_segments}"
        
        if cache_key in self.cache:
            logger.info(f"📋 Using cached cut points for {video_path.name}")
            return self.cache[cache_key]
        
        logger.info(f"🔍 Analyzing optimal cut points for {video_path.name}")
        
        if not video_path.exists():
            return OptimalCutPoints(
                cut_points=[0.0],
                method=AnalysisMethod.HEURISTIC_ANALYSIS,
                confidence=0.0,
                reasoning=f"File not found: {video_path}",
                segment_durations=[0.0],
                quality_score=0.0
            )
        
        try:
            # Get video duration first
            duration = await self._get_video_duration(video_path)
            
            if duration <= 0:
                raise ValueError(f"Invalid video duration: {duration}")
            
            # Try multiple analysis methods in order of preference
            methods = [
                (AnalysisMethod.FFPROBE_KEYFRAMES, self._analyze_keyframes_method),
                (AnalysisMethod.SCENE_DETECTION, self._analyze_scene_boundaries_method),
                (AnalysisMethod.HEURISTIC_ANALYSIS, self._analyze_heuristic_method)
            ]
            
            for method, analyzer_func in methods:
                try:
                    logger.info(f"  🧠 Trying {method.value} method...")
                    result = await analyzer_func(video_path, target_segments, duration, target_duration)
                    
                    if result.confidence > 0.5:  # Good enough confidence
                        logger.info(f"  ✅ {method.value} succeeded with confidence {result.confidence:.2f}")
                        self.cache[cache_key] = result
                        return result
                    else:
                        logger.info(f"  ⚠️ {method.value} low confidence ({result.confidence:.2f}), trying next method")
                        
                except Exception as e:
                    logger.warning(f"  ❌ {method.value} failed: {e}")
                    continue
            
            # All methods failed - return basic fallback
            logger.warning(f"⚠️ All analysis methods failed for {video_path.name}, using uniform fallback")
            return OptimalCutPoints(
                cut_points=self._generate_uniform_cut_points(duration, target_segments),
                method=AnalysisMethod.HEURISTIC_ANALYSIS,
                confidence=0.3,
                reasoning="All advanced methods failed - uniform fallback",
                segment_durations=self._calculate_segment_durations(
                    self._generate_uniform_cut_points(duration, target_segments)
                ),
                quality_score=0.3
            )
            
        except Exception as e:
            logger.error(f"❌ Cut point detection failed for {video_path}: {e}")
            return OptimalCutPoints(
                cut_points=[0.0],
                method=AnalysisMethod.HEURISTIC_ANALYSIS,
                confidence=0.0,
                reasoning=f"Analysis failed: {e}",
                segment_durations=[0.0],
                quality_score=0.0
            )
    
    async def _analyze_keyframes_method(self, 
                                      video_path: Path, 
                                      target_segments: int,
                                      duration: float,
                                      target_duration: Optional[float]) -> OptimalCutPoints:
        """Analyze using FFprobe keyframe detection"""
        
        keyframes = await self.analyze_keyframes(video_path)
        
        if len(keyframes) < target_segments:
            # Not enough keyframes - fall back to scene detection
            raise ValueError(f"Insufficient keyframes: {len(keyframes)} < {target_segments}")
        
        # Select keyframes that provide good segment distribution
        selected_keyframes = self._select_optimal_keyframes(keyframes, target_segments, duration)
        
        cut_points = [kf.timestamp for kf in selected_keyframes]
        segment_durations = self._calculate_segment_durations(cut_points)
        
        # Calculate quality score based on keyframe distribution
        quality_score = self._calculate_keyframe_quality_score(keyframes, cut_points, duration)
        
        return OptimalCutPoints(
            cut_points=cut_points,
            method=AnalysisMethod.FFPROBE_KEYFRAMES,
            confidence=min(quality_score + 0.2, 1.0),  # Boost keyframe method confidence
            reasoning=f"Selected {len(cut_points)} keyframes from {len(keyframes)} available, "
                     f"avg segment: {duration/len(cut_points):.1f}s",
            segment_durations=segment_durations,
            quality_score=quality_score
        )
    
    async def _analyze_scene_boundaries_method(self,
                                             video_path: Path,
                                             target_segments: int, 
                                             duration: float,
                                             target_duration: Optional[float]) -> OptimalCutPoints:
        """Analyze using scene boundary detection"""
        
        scene_boundaries = await self.detect_scene_boundaries(video_path)
        
        if len(scene_boundaries) < target_segments - 1:
            raise ValueError(f"Insufficient scene boundaries: {len(scene_boundaries)} < {target_segments-1}")
        
        # Select scene boundaries that create good segments
        selected_boundaries = self._select_optimal_boundaries(scene_boundaries, target_segments, duration)
        
        # Always include start time
        cut_points = [0.0] + [sb.timestamp for sb in selected_boundaries]
        cut_points = sorted(set(cut_points))  # Remove duplicates and sort
        
        segment_durations = self._calculate_segment_durations(cut_points)
        quality_score = sum(sb.confidence for sb in selected_boundaries) / len(selected_boundaries)
        
        return OptimalCutPoints(
            cut_points=cut_points,
            method=AnalysisMethod.SCENE_DETECTION,
            confidence=quality_score,
            reasoning=f"Scene boundaries detected: {len(scene_boundaries)}, "
                     f"selected {len(selected_boundaries)} for {target_segments} segments",
            segment_durations=segment_durations,
            quality_score=quality_score
        )
    
    async def _analyze_heuristic_method(self,
                                      video_path: Path,
                                      target_segments: int,
                                      duration: float, 
                                      target_duration: Optional[float]) -> OptimalCutPoints:
        """Heuristic analysis based on video properties"""
        
        # Get basic video information
        video_info = await self._get_video_info(video_path)
        complexity = await self.calculate_complexity_metrics(video_path)
        
        # Determine cut strategy based on complexity and duration
        if complexity.overall_complexity < 0.5:
            # Simple video - uniform cuts are probably OK
            cut_points = self._generate_uniform_cut_points(duration, target_segments)
            confidence = 0.6
            reasoning = "Low complexity video - uniform distribution suitable"
        
        elif duration > 120:  # Long video
            # For long videos, create more cuts at the beginning where content usually changes more
            cut_points = self._generate_front_loaded_cut_points(duration, target_segments)
            confidence = 0.7
            reasoning = "Long video - front-loaded segment distribution"
            
        else:
            # Medium complexity - try to avoid obvious problem areas
            cut_points = self._generate_smart_heuristic_cut_points(duration, target_segments, video_info)
            confidence = 0.65
            reasoning = "Heuristic analysis based on video properties"
        
        segment_durations = self._calculate_segment_durations(cut_points)
        
        return OptimalCutPoints(
            cut_points=cut_points,
            method=AnalysisMethod.HEURISTIC_ANALYSIS,
            confidence=confidence,
            reasoning=reasoning,
            segment_durations=segment_durations,
            quality_score=complexity.overall_complexity
        )
    
    async def analyze_keyframes(self, video_path: Union[str, Path]) -> List[KeyframeInfo]:
        """Analyze keyframes in video using FFprobe"""
        
        video_path = Path(video_path)
        
        if not video_path.exists():
            return []
        
        try:
            # Use FFprobe to get keyframe information with better timestamp handling
            cmd = [
                'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                '-show_entries', 'frame=key_frame,best_effort_timestamp_time,pict_type,pkt_size',
                '-of', 'csv=p=0', str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
            
            keyframes = []
            for line_num, line in enumerate(result.stdout.strip().split('\n')):
                if not line:
                    continue
                    
                try:
                    # Parse CSV: key_frame,timestamp,pict_type,pkt_size
                    parts = line.split(',')
                    if len(parts) >= 3:
                        key_frame = int(parts[0]) if parts[0] and parts[0].isdigit() else 0
                        timestamp = float(parts[1]) if parts[1] and parts[1] != 'N/A' else None
                        pict_type = parts[2].strip() if parts[2] else 'U'
                        pkt_size = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                        
                        if key_frame == 1 and timestamp is not None:  # Is a keyframe with valid timestamp
                            keyframes.append(KeyframeInfo(
                                timestamp=timestamp,
                                frame_type=pict_type,
                                scene_boundary=pict_type == 'I',  # I-frames are more likely scene boundaries
                                confidence=0.9 if pict_type == 'I' else 0.7,
                                size_bytes=pkt_size
                            ))
                            
                except (ValueError, IndexError) as e:
                    logger.warning(f"⚠️ Skipping malformed line {line_num}: {line} ({e})")
                    continue
            
            logger.info(f"🔍 Found {len(keyframes)} keyframes in {video_path.name}")
            return sorted(keyframes, key=lambda x: x.timestamp)
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Keyframe analysis timed out for {video_path}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFprobe failed for {video_path}: {e.stderr}")
            return []
        except Exception as e:
            logger.error(f"❌ Keyframe analysis failed for {video_path}: {e}")
            return []
    
    async def detect_scene_boundaries(self, 
                                    video_path: Union[str, Path],
                                    sensitivity: float = 0.3) -> List[SceneBoundary]:
        """Detect scene boundaries using FFmpeg scene detection"""
        
        video_path = Path(video_path)
        
        if not video_path.exists():
            return []
        
        try:
            # Use FFprobe with scene detection filter
            cmd = [
                'ffprobe', '-f', 'lavfi',
                '-i', f'movie={video_path},select=gt(scene\\,{sensitivity})',
                '-show_entries', 'frame=pts_time',
                '-of', 'csv=p=0'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
            
            boundaries = []
            prev_timestamp = 0.0
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    timestamp = float(line)
                    scene_duration = timestamp - prev_timestamp
                    
                    boundaries.append(SceneBoundary(
                        timestamp=timestamp,
                        confidence=min(sensitivity + 0.4, 1.0),  # Higher sensitivity = higher confidence
                        change_type="cut",  # Scene filter detects cuts primarily
                        previous_scene_duration=scene_duration if scene_duration > 0 else None
                    ))
                    
                    prev_timestamp = timestamp
                    
                except ValueError as e:
                    logger.warning(f"⚠️ Invalid scene boundary timestamp: {line} ({e})")
                    continue
            
            logger.info(f"🎬 Found {len(boundaries)} scene boundaries in {video_path.name}")
            return sorted(boundaries, key=lambda x: x.timestamp)
            
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Scene detection timed out for {video_path}")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Scene detection failed for {video_path}: {e.stderr}")
            return []
        except Exception as e:
            logger.error(f"❌ Scene boundary detection failed for {video_path}: {e}")
            return []
    
    async def calculate_complexity_metrics(self, video_path: Union[str, Path]) -> ComplexityMetrics:
        """Calculate video complexity metrics for processing estimation"""
        
        video_path = Path(video_path)
        
        if not video_path.exists():
            return ComplexityMetrics(
                resolution_factor=0.0,
                duration_factor=0.0,
                motion_complexity=0.0,
                color_complexity=0.0,
                overall_complexity=0.0,
                processing_recommendation="file_not_found"
            )
        
        try:
            # Get basic video properties
            video_info = await self._get_video_info(video_path)
            
            # Resolution complexity (relative to 1080p)
            width = video_info.get('width', 1920)
            height = video_info.get('height', 1080)
            pixels = width * height
            reference_pixels = 1920 * 1080
            resolution_factor = pixels / reference_pixels
            
            # Duration complexity (processing time factor)
            duration = video_info.get('duration', 0.0)
            duration_factor = min(duration / 60.0, 2.0)  # Cap at 2x for very long videos
            
            # Estimate motion complexity from bitrate
            bitrate = video_info.get('bit_rate', 0)
            if bitrate > 0:
                # Higher bitrate often indicates more motion/complexity
                motion_complexity = min(bitrate / 5000000, 2.0)  # Relative to 5Mbps reference
            else:
                motion_complexity = 0.5  # Default moderate complexity
            
            # Color complexity estimate (would need histogram analysis for precision)
            # For now, estimate from codec and profile
            codec = video_info.get('codec_name', 'unknown')
            color_complexity = 0.8 if codec in ['h264', 'h265'] else 0.5
            
            # Overall complexity score
            overall_complexity = (
                resolution_factor * 0.3 +
                duration_factor * 0.2 + 
                motion_complexity * 0.3 +
                color_complexity * 0.2
            )
            
            # Processing recommendation
            if overall_complexity < 0.5:
                processing_rec = "fast_processing"
            elif overall_complexity < 1.0:
                processing_rec = "standard_processing"
            elif overall_complexity < 1.5:
                processing_rec = "careful_processing"
            else:
                processing_rec = "slow_careful_processing"
            
            return ComplexityMetrics(
                resolution_factor=resolution_factor,
                duration_factor=duration_factor,
                motion_complexity=motion_complexity,
                color_complexity=color_complexity,
                overall_complexity=overall_complexity,
                processing_recommendation=processing_rec
            )
            
        except Exception as e:
            logger.error(f"❌ Complexity analysis failed for {video_path}: {e}")
            return ComplexityMetrics(
                resolution_factor=0.5,
                duration_factor=0.5,
                motion_complexity=0.5,
                color_complexity=0.5,
                overall_complexity=0.5,
                processing_recommendation="analysis_failed_use_defaults"
            )
    
    # Helper methods
    async def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration using FFprobe"""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                   '-of', 'csv=p=0', str(video_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"❌ Could not get duration for {video_path}: {e}")
            return 0.0
    
    async def _get_video_info(self, video_path: Path) -> Dict[str, Any]:
        """Get comprehensive video information"""
        try:
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                   '-show_format', '-show_streams', str(video_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
            
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'codec_name': video_stream.get('codec_name', 'unknown'),
                'profile': video_stream.get('profile', 'unknown')
            }
        except Exception as e:
            logger.error(f"❌ Could not get video info for {video_path}: {e}")
            return {}
    
    def _select_optimal_keyframes(self, 
                                 keyframes: List[KeyframeInfo], 
                                 target_segments: int,
                                 duration: float) -> List[KeyframeInfo]:
        """Select keyframes that provide optimal segment distribution"""
        
        if len(keyframes) <= target_segments:
            return keyframes
        
        # Calculate ideal timestamps for segments
        ideal_interval = duration / target_segments
        ideal_timestamps = [i * ideal_interval for i in range(target_segments)]
        
        selected = []
        for ideal_ts in ideal_timestamps:
            # Find keyframe closest to ideal timestamp
            closest_kf = min(keyframes, key=lambda kf: abs(kf.timestamp - ideal_ts))
            if closest_kf not in selected:
                selected.append(closest_kf)
        
        return sorted(selected, key=lambda x: x.timestamp)
    
    def _select_optimal_boundaries(self,
                                  boundaries: List[SceneBoundary],
                                  target_segments: int,
                                  duration: float) -> List[SceneBoundary]:
        """Select scene boundaries that create good segment distribution"""
        
        if len(boundaries) <= target_segments - 1:
            return boundaries
        
        # Sort by confidence and select best boundaries
        sorted_boundaries = sorted(boundaries, key=lambda x: x.confidence, reverse=True)
        selected = sorted_boundaries[:target_segments-1]
        
        return sorted(selected, key=lambda x: x.timestamp)
    
    def _generate_uniform_cut_points(self, duration: float, target_segments: int) -> List[float]:
        """Generate uniform cut points (fallback method)"""
        if target_segments <= 1:
            return [0.0]
        
        interval = duration / target_segments
        return [i * interval for i in range(target_segments)]
    
    def _generate_front_loaded_cut_points(self, duration: float, target_segments: int) -> List[float]:
        """Generate front-loaded cut points for long videos"""
        if target_segments <= 1:
            return [0.0]
        
        # More cuts at the beginning, fewer at the end
        cut_points = [0.0]
        remaining_time = duration
        remaining_segments = target_segments - 1
        
        for i in range(1, target_segments):
            # Shorter segments at the beginning
            if i <= target_segments // 2:
                segment_duration = remaining_time * 0.15  # 15% of remaining time
            else:
                segment_duration = remaining_time / remaining_segments
            
            cut_points.append(cut_points[-1] + segment_duration)
            remaining_time -= segment_duration
            remaining_segments -= 1
        
        return cut_points[:-1]  # Remove last point (would be end of video)
    
    def _generate_smart_heuristic_cut_points(self, 
                                           duration: float, 
                                           target_segments: int,
                                           video_info: Dict[str, Any]) -> List[float]:
        """Generate smart heuristic cut points based on video properties"""
        
        # Start with uniform distribution
        uniform_points = self._generate_uniform_cut_points(duration, target_segments)
        
        # Adjust based on video properties
        if video_info.get('bit_rate', 0) > 10000000:  # High bitrate video
            # Slightly favor earlier cuts where there's likely more action
            adjustment_factor = 0.9
            adjusted_points = [0.0]
            for i in range(1, len(uniform_points)):
                adjusted_time = uniform_points[i] * adjustment_factor
                adjusted_points.append(min(adjusted_time, duration * 0.95))
        else:
            adjusted_points = uniform_points
        
        return adjusted_points
    
    def _calculate_segment_durations(self, cut_points: List[float]) -> List[float]:
        """Calculate duration of each segment from cut points"""
        if len(cut_points) <= 1:
            return [0.0]
        
        durations = []
        for i in range(len(cut_points) - 1):
            duration = cut_points[i + 1] - cut_points[i]
            durations.append(duration)
        
        return durations
    
    def _calculate_keyframe_quality_score(self, 
                                        keyframes: List[KeyframeInfo],
                                        cut_points: List[float],
                                        duration: float) -> float:
        """Calculate quality score based on keyframe alignment"""
        
        if not keyframes or not cut_points:
            return 0.0
        
        # Score based on how well cut points align with keyframes
        total_alignment_score = 0.0
        
        for cut_point in cut_points:
            # Find closest keyframe to this cut point
            closest_distance = min(abs(kf.timestamp - cut_point) for kf in keyframes)
            
            # Score: 1.0 for perfect alignment, decreasing with distance
            alignment_score = max(0.0, 1.0 - (closest_distance / 2.0))  # 2 second tolerance
            total_alignment_score += alignment_score
        
        return total_alignment_score / len(cut_points)

# Convenience functions for direct API usage
async def detect_optimal_cut_points(video_path: Union[str, Path],
                                   target_segments: int = 4,
                                   target_duration: Optional[float] = None) -> OptimalCutPoints:
    """
    Convenience function to detect optimal cut points.
    
    This is the KEY API that solves the 9.7s-29s timing differences
    found in MCP uniform vs keyframe-aligned comparison.
    """
    analyzer = VideoIntelligenceAnalyzer()
    return await analyzer.detect_optimal_cut_points(video_path, target_segments, target_duration)

async def analyze_keyframes(video_path: Union[str, Path]) -> List[KeyframeInfo]:
    """Convenience function for keyframe analysis"""
    analyzer = VideoIntelligenceAnalyzer()
    return await analyzer.analyze_keyframes(video_path)

async def detect_scene_boundaries(video_path: Union[str, Path], sensitivity: float = 0.3) -> List[SceneBoundary]:
    """Convenience function for scene boundary detection"""
    analyzer = VideoIntelligenceAnalyzer()
    return await analyzer.detect_scene_boundaries(video_path, sensitivity)

async def calculate_complexity_metrics(video_path: Union[str, Path]) -> ComplexityMetrics:
    """Convenience function for complexity analysis"""
    analyzer = VideoIntelligenceAnalyzer()
    return await analyzer.calculate_complexity_metrics(video_path)
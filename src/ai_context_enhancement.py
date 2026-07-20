#!/usr/bin/env python3
"""
AI Context Enhancement - Priority 3: AI Context Enhancement

Provides rich contextual information to AI systems for better decision making
in video processing tasks. This addresses the need for more intelligent 
tool selection and parameter optimization.

Key Features:
- Video complexity scoring with detailed explanations
- Historical performance context from previous operations  
- Intelligent tool selection recommendations
- Parameter optimization suggestions based on video characteristics
- Cost-benefit analysis for different processing approaches
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ProcessingComplexity(Enum):
    """Video processing complexity levels"""
    TRIVIAL = "trivial"
    SIMPLE = "simple" 
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXTREME = "extreme"

class ToolRecommendation(Enum):
    """Tool usage recommendations"""
    DIRECT_FFMPEG = "direct_ffmpeg"
    KEYFRAME_ALIGN = "keyframe_align"
    CROSSFADE_CONCAT = "crossfade_concat"
    NORMALIZE_FIRST = "normalize_first"
    SEGMENT_PROCESS = "segment_process"

@dataclass
class VideoCharacteristics:
    """Detailed video characteristics for AI context"""
    duration: float
    resolution: Tuple[int, int] 
    bitrate: int
    codec: str
    frame_rate: float
    has_audio: bool
    estimated_keyframes: int
    motion_level: str  # "low", "medium", "high"
    color_complexity: str  # "simple", "moderate", "complex"
    file_size_mb: float

@dataclass
class ProcessingHistory:
    """Historical processing performance data"""
    tool_name: str
    video_characteristics: VideoCharacteristics
    processing_time: float
    success: bool
    cpu_usage: float
    memory_usage_mb: float
    output_quality: float  # 0-1 score
    timestamp: datetime
    error_message: Optional[str] = None

@dataclass
class ContextualRecommendation:
    """AI-enhanced tool recommendation with rich context"""
    recommended_tool: ToolRecommendation
    confidence: float
    reasoning: str
    expected_processing_time: float
    expected_cpu_usage: float
    expected_memory_mb: float
    cost_estimate: float
    quality_expectation: float
    risk_factors: List[str]
    optimization_tips: List[str]
    fallback_options: List[ToolRecommendation]

@dataclass
class AIContext:
    """Complete AI context package for video processing decision"""
    video_analysis: VideoCharacteristics
    complexity_assessment: ProcessingComplexity
    historical_insights: List[ProcessingHistory]
    tool_recommendations: List[ContextualRecommendation]
    resource_constraints: Dict[str, Any]
    performance_predictions: Dict[str, float]
    contextual_warnings: List[str]
    optimization_opportunities: List[str]

class AIContextEnhancer:
    """
    AI Context Enhancement system that provides rich contextual information
    for intelligent video processing decisions.
    """
    
    def __init__(self, history_retention_days: int = 30):
        self.history_retention_days = history_retention_days
        self.processing_history: List[ProcessingHistory] = []
        self.performance_baselines = self._initialize_performance_baselines()
        
        # Load historical data if available
        self._load_processing_history()
    
    async def generate_ai_context(self, 
                                video_path: Union[str, Path],
                                target_operation: str,
                                resource_constraints: Optional[Dict[str, Any]] = None) -> AIContext:
        """
        Generate comprehensive AI context for video processing decision making.
        
        This is the main API that provides rich contextual information to AI systems.
        
        Args:
            video_path: Path to video file for analysis
            target_operation: Type of operation (concat, segment, transcode, etc)
            resource_constraints: Optional resource limits (cpu, memory, time)
            
        Returns:
            AIContext with comprehensive decision-making information
        """
        
        logger.info(f"🧠 Generating AI context for {target_operation} on {Path(video_path).name}")
        
        # Analyze video characteristics
        video_analysis = await self._analyze_video_characteristics(video_path)
        
        # Assess processing complexity
        complexity = self._assess_processing_complexity(video_analysis, target_operation)
        
        # Get relevant historical insights
        historical_insights = self._get_relevant_history(video_analysis, target_operation)
        
        # Generate tool recommendations with rich context
        tool_recommendations = await self._generate_contextual_recommendations(
            video_analysis, target_operation, historical_insights, resource_constraints
        )
        
        # Predict performance characteristics
        performance_predictions = self._predict_performance(
            video_analysis, target_operation, historical_insights
        )
        
        # Identify optimization opportunities
        optimization_opportunities = self._identify_optimization_opportunities(
            video_analysis, target_operation, performance_predictions
        )
        
        # Generate contextual warnings
        contextual_warnings = self._generate_contextual_warnings(
            video_analysis, target_operation, resource_constraints
        )
        
        ai_context = AIContext(
            video_analysis=video_analysis,
            complexity_assessment=complexity,
            historical_insights=historical_insights,
            tool_recommendations=tool_recommendations,
            resource_constraints=resource_constraints or {},
            performance_predictions=performance_predictions,
            contextual_warnings=contextual_warnings,
            optimization_opportunities=optimization_opportunities
        )
        
        logger.info(f"✅ AI context generated: {complexity.value} complexity, "
                   f"{len(tool_recommendations)} recommendations, "
                   f"{len(optimization_opportunities)} optimizations")
        
        return ai_context
    
    async def _analyze_video_characteristics(self, video_path: Union[str, Path]) -> VideoCharacteristics:
        """Analyze video file to extract detailed characteristics"""
        
        video_path = Path(video_path)
        
        if not video_path.exists():
            return VideoCharacteristics(
                duration=0.0,
                resolution=(0, 0),
                bitrate=0,
                codec="unknown",
                frame_rate=0.0,
                has_audio=False,
                estimated_keyframes=0,
                motion_level="unknown",
                color_complexity="unknown", 
                file_size_mb=0.0
            )
        
        try:
            # Get comprehensive video info using ffprobe
            import subprocess
            cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                   '-show_format', '-show_streams', str(video_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=15)
            
            data = json.loads(result.stdout)
            format_info = data.get('format', {})
            video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
            audio_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
            
            duration = float(format_info.get('duration', 0))
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            bitrate = int(format_info.get('bit_rate', 0))
            codec = video_stream.get('codec_name', 'unknown')
            
            # Calculate frame rate
            r_frame_rate = video_stream.get('r_frame_rate', '0/1')
            if '/' in r_frame_rate:
                num, den = map(int, r_frame_rate.split('/'))
                frame_rate = num / den if den != 0 else 0.0
            else:
                frame_rate = float(r_frame_rate)
            
            # Estimate keyframes (typically every 2-10 seconds depending on codec)
            keyframe_interval = 5.0  # Conservative estimate
            estimated_keyframes = max(1, int(duration / keyframe_interval))
            
            # Assess motion level based on bitrate and resolution
            pixels_per_second = (width * height * frame_rate)
            if pixels_per_second > 0:
                bitrate_per_pixel = bitrate / pixels_per_second
                if bitrate_per_pixel > 0.1:
                    motion_level = "high"
                elif bitrate_per_pixel > 0.05:
                    motion_level = "medium" 
                else:
                    motion_level = "low"
            else:
                motion_level = "unknown"
            
            # Assess color complexity based on codec and bitrate
            if codec in ['h264', 'h265'] and bitrate > 5000000:
                color_complexity = "complex"
            elif bitrate > 2000000:
                color_complexity = "moderate"
            else:
                color_complexity = "simple"
            
            file_size_mb = video_path.stat().st_size / 1024 / 1024
            
            return VideoCharacteristics(
                duration=duration,
                resolution=(width, height),
                bitrate=bitrate,
                codec=codec,
                frame_rate=frame_rate,
                has_audio=len(audio_streams) > 0,
                estimated_keyframes=estimated_keyframes,
                motion_level=motion_level,
                color_complexity=color_complexity,
                file_size_mb=file_size_mb
            )
            
        except Exception as e:
            logger.error(f"❌ Video analysis failed for {video_path}: {e}")
            
            # Return basic file info as fallback
            file_size_mb = video_path.stat().st_size / 1024 / 1024 if video_path.exists() else 0.0
            
            return VideoCharacteristics(
                duration=0.0,
                resolution=(0, 0),
                bitrate=0,
                codec="analysis_failed",
                frame_rate=0.0,
                has_audio=False,
                estimated_keyframes=0,
                motion_level="unknown",
                color_complexity="unknown",
                file_size_mb=file_size_mb
            )
    
    def _assess_processing_complexity(self, 
                                    video_analysis: VideoCharacteristics,
                                    target_operation: str) -> ProcessingComplexity:
        """Assess the processing complexity level for AI context"""
        
        complexity_score = 0.0
        
        # Duration factor
        if video_analysis.duration > 300:  # > 5 minutes
            complexity_score += 2.0
        elif video_analysis.duration > 120:  # > 2 minutes
            complexity_score += 1.0
        elif video_analysis.duration > 30:  # > 30 seconds
            complexity_score += 0.5
        
        # Resolution factor
        width, height = video_analysis.resolution
        pixels = width * height
        if pixels > 3840 * 2160:  # 4K+
            complexity_score += 3.0
        elif pixels > 1920 * 1080:  # > 1080p
            complexity_score += 2.0
        elif pixels > 1280 * 720:  # > 720p
            complexity_score += 1.0
        
        # Bitrate factor
        if video_analysis.bitrate > 20000000:  # > 20Mbps
            complexity_score += 2.0
        elif video_analysis.bitrate > 10000000:  # > 10Mbps
            complexity_score += 1.0
        elif video_analysis.bitrate > 5000000:  # > 5Mbps
            complexity_score += 0.5
        
        # Motion complexity factor
        motion_factors = {"high": 2.0, "medium": 1.0, "low": 0.2, "unknown": 0.5}
        complexity_score += motion_factors.get(video_analysis.motion_level, 0.5)
        
        # Operation-specific factors
        operation_factors = {
            "concat": 1.0,
            "segment": 0.8,
            "transcode": 2.0,
            "normalize": 1.5,
            "crossfade": 1.8,
            "stabilize": 3.0,
            "denoise": 2.5
        }
        complexity_score *= operation_factors.get(target_operation, 1.0)
        
        # Map score to complexity levels
        if complexity_score < 1.0:
            return ProcessingComplexity.TRIVIAL
        elif complexity_score < 3.0:
            return ProcessingComplexity.SIMPLE
        elif complexity_score < 6.0:
            return ProcessingComplexity.MODERATE
        elif complexity_score < 10.0:
            return ProcessingComplexity.COMPLEX
        else:
            return ProcessingComplexity.EXTREME
    
    def _get_relevant_history(self, 
                            video_analysis: VideoCharacteristics,
                            target_operation: str,
                            max_results: int = 10) -> List[ProcessingHistory]:
        """Get relevant historical processing data for context"""
        
        relevant_history = []
        
        for history_item in self.processing_history:
            if history_item.tool_name == target_operation:
                # Calculate similarity score based on video characteristics
                similarity_score = self._calculate_similarity_score(
                    video_analysis, history_item.video_characteristics
                )
                
                if similarity_score > 0.3:  # At least 30% similar
                    relevant_history.append((similarity_score, history_item))
        
        # Sort by similarity and return top results
        relevant_history.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in relevant_history[:max_results]]
    
    def _calculate_similarity_score(self, 
                                  current: VideoCharacteristics,
                                  historical: VideoCharacteristics) -> float:
        """Calculate similarity score between video characteristics"""
        
        score = 0.0
        total_weight = 0.0
        
        # Duration similarity (weight: 0.3)
        duration_diff = abs(current.duration - historical.duration)
        max_duration = max(current.duration, historical.duration)
        if max_duration > 0:
            duration_similarity = 1.0 - min(duration_diff / max_duration, 1.0)
            score += duration_similarity * 0.3
            total_weight += 0.3
        
        # Resolution similarity (weight: 0.2)
        current_pixels = current.resolution[0] * current.resolution[1]
        historical_pixels = historical.resolution[0] * historical.resolution[1]
        if max(current_pixels, historical_pixels) > 0:
            pixel_diff = abs(current_pixels - historical_pixels)
            max_pixels = max(current_pixels, historical_pixels)
            resolution_similarity = 1.0 - min(pixel_diff / max_pixels, 1.0)
            score += resolution_similarity * 0.2
            total_weight += 0.2
        
        # Bitrate similarity (weight: 0.15)
        if max(current.bitrate, historical.bitrate) > 0:
            bitrate_diff = abs(current.bitrate - historical.bitrate)
            max_bitrate = max(current.bitrate, historical.bitrate)
            bitrate_similarity = 1.0 - min(bitrate_diff / max_bitrate, 1.0)
            score += bitrate_similarity * 0.15
            total_weight += 0.15
        
        # Codec similarity (weight: 0.1)
        codec_similarity = 1.0 if current.codec == historical.codec else 0.5
        score += codec_similarity * 0.1
        total_weight += 0.1
        
        # Motion level similarity (weight: 0.15)
        motion_similarity = 1.0 if current.motion_level == historical.motion_level else 0.3
        score += motion_similarity * 0.15
        total_weight += 0.15
        
        # File size similarity (weight: 0.1)
        if max(current.file_size_mb, historical.file_size_mb) > 0:
            size_diff = abs(current.file_size_mb - historical.file_size_mb)
            max_size = max(current.file_size_mb, historical.file_size_mb)
            size_similarity = 1.0 - min(size_diff / max_size, 1.0)
            score += size_similarity * 0.1
            total_weight += 0.1
        
        return score / total_weight if total_weight > 0 else 0.0
    
    async def _generate_contextual_recommendations(self,
                                                 video_analysis: VideoCharacteristics,
                                                 target_operation: str,
                                                 historical_insights: List[ProcessingHistory],
                                                 resource_constraints: Optional[Dict[str, Any]]) -> List[ContextualRecommendation]:
        """Generate tool recommendations with rich contextual information"""
        
        recommendations = []
        
        # Direct FFmpeg recommendation
        direct_rec = self._evaluate_direct_ffmpeg(video_analysis, target_operation, historical_insights)
        if direct_rec:
            recommendations.append(direct_rec)
        
        # Keyframe-aligned recommendation
        keyframe_rec = self._evaluate_keyframe_align(video_analysis, target_operation, historical_insights)
        if keyframe_rec:
            recommendations.append(keyframe_rec)
        
        # Crossfade concatenation recommendation
        if target_operation in ['concat', 'merge']:
            crossfade_rec = self._evaluate_crossfade_concat(video_analysis, historical_insights)
            if crossfade_rec:
                recommendations.append(crossfade_rec)
        
        # Normalize first recommendation
        normalize_rec = self._evaluate_normalize_first(video_analysis, target_operation, historical_insights)
        if normalize_rec:
            recommendations.append(normalize_rec)
        
        # Sort by confidence and apply resource constraints
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        # Apply resource constraints filtering
        if resource_constraints:
            recommendations = self._filter_by_resource_constraints(recommendations, resource_constraints)
        
        return recommendations[:5]  # Return top 5 recommendations
    
    def _evaluate_direct_ffmpeg(self, 
                              video_analysis: VideoCharacteristics,
                              target_operation: str,
                              historical_insights: List[ProcessingHistory]) -> Optional[ContextualRecommendation]:
        """Evaluate direct FFmpeg approach"""
        
        # Calculate base confidence based on video characteristics
        confidence = 0.7  # Base confidence for direct FFmpeg
        
        # Adjust based on complexity
        if video_analysis.duration < 60 and video_analysis.file_size_mb < 100:
            confidence += 0.2  # Simple videos work well with direct approach
        
        if video_analysis.codec in ['h264', 'h265']:
            confidence += 0.1  # Standard codecs work well
        
        # Adjust based on historical data
        direct_history = [h for h in historical_insights if 'ffmpeg' in h.tool_name]
        if direct_history:
            avg_success = sum(1 for h in direct_history if h.success) / len(direct_history)
            confidence = (confidence + avg_success) / 2
        
        # Performance predictions based on video characteristics
        base_time = video_analysis.duration * 0.1  # 10% of video duration as base
        expected_time = base_time * (1 + video_analysis.file_size_mb / 1000)  # Size factor
        
        expected_cpu = min(80.0, 20.0 + video_analysis.file_size_mb / 10)  # CPU usage estimate
        expected_memory = min(1000.0, 100.0 + video_analysis.file_size_mb * 2)  # Memory estimate
        
        risk_factors = []
        if video_analysis.duration > 300:
            risk_factors.append("Long duration may cause timeout issues")
        if video_analysis.file_size_mb > 500:
            risk_factors.append("Large file size may cause memory issues")
        if video_analysis.codec not in ['h264', 'h265', 'vp8', 'vp9']:
            risk_factors.append(f"Uncommon codec {video_analysis.codec} may cause compatibility issues")
        
        optimization_tips = []
        if video_analysis.bitrate > 10000000:
            optimization_tips.append("Consider reducing bitrate for faster processing")
        if video_analysis.resolution[0] > 1920:
            optimization_tips.append("Consider downscaling resolution for speed improvement")
        
        fallback_options = [ToolRecommendation.SEGMENT_PROCESS, ToolRecommendation.NORMALIZE_FIRST]
        
        return ContextualRecommendation(
            recommended_tool=ToolRecommendation.DIRECT_FFMPEG,
            confidence=min(confidence, 1.0),
            reasoning=f"Direct FFmpeg suitable for {video_analysis.codec} video, "
                     f"{video_analysis.file_size_mb:.1f}MB file size",
            expected_processing_time=expected_time,
            expected_cpu_usage=expected_cpu,
            expected_memory_mb=expected_memory,
            cost_estimate=0.01 + (video_analysis.duration / 60) * 0.02,
            quality_expectation=0.9,
            risk_factors=risk_factors,
            optimization_tips=optimization_tips,
            fallback_options=fallback_options
        )
    
    def _evaluate_keyframe_align(self,
                               video_analysis: VideoCharacteristics,
                               target_operation: str,
                               historical_insights: List[ProcessingHistory]) -> Optional[ContextualRecommendation]:
        """Evaluate keyframe-aligned approach"""
        
        confidence = 0.8  # Higher base confidence for keyframe alignment
        
        # Keyframe alignment is especially good for concatenation
        if target_operation in ['concat', 'merge']:
            confidence += 0.15
        
        # Works well with standard codecs
        if video_analysis.codec in ['h264', 'h265']:
            confidence += 0.05
        
        # Adjust for estimated keyframe count
        if video_analysis.estimated_keyframes > 10:
            confidence += 0.05  # More keyframes = better alignment options
        
        expected_time = video_analysis.duration * 0.15  # Slightly slower than direct
        expected_cpu = min(70.0, 25.0 + video_analysis.file_size_mb / 8)
        expected_memory = min(800.0, 120.0 + video_analysis.file_size_mb * 1.5)
        
        risk_factors = []
        if video_analysis.estimated_keyframes < 3:
            risk_factors.append("Few keyframes may limit alignment options")
        
        optimization_tips = [
            "Keyframe alignment provides smoother transitions",
            "Best for concatenating videos with similar characteristics"
        ]
        
        fallback_options = [ToolRecommendation.DIRECT_FFMPEG, ToolRecommendation.CROSSFADE_CONCAT]
        
        return ContextualRecommendation(
            recommended_tool=ToolRecommendation.KEYFRAME_ALIGN,
            confidence=min(confidence, 1.0),
            reasoning=f"Keyframe alignment optimal for {target_operation} with "
                     f"{video_analysis.estimated_keyframes} estimated keyframes",
            expected_processing_time=expected_time,
            expected_cpu_usage=expected_cpu,
            expected_memory_mb=expected_memory,
            cost_estimate=0.015 + (video_analysis.duration / 60) * 0.025,
            quality_expectation=0.95,
            risk_factors=risk_factors,
            optimization_tips=optimization_tips,
            fallback_options=fallback_options
        )
    
    def _evaluate_crossfade_concat(self,
                                 video_analysis: VideoCharacteristics,
                                 historical_insights: List[ProcessingHistory]) -> Optional[ContextualRecommendation]:
        """Evaluate crossfade concatenation approach"""
        
        confidence = 0.75
        
        # Good for videos with audio
        if video_analysis.has_audio:
            confidence += 0.1
        
        # Better for high-quality videos
        if video_analysis.bitrate > 5000000:
            confidence += 0.05
        
        expected_time = video_analysis.duration * 0.25  # Slower due to crossfading
        expected_cpu = min(85.0, 30.0 + video_analysis.file_size_mb / 6)
        expected_memory = min(1200.0, 150.0 + video_analysis.file_size_mb * 2.5)
        
        risk_factors = []
        if not video_analysis.has_audio:
            risk_factors.append("No audio track - crossfade benefits limited to video only")
        
        optimization_tips = [
            "Crossfade provides smoother audio/video transitions",
            "Consider adjusting crossfade duration based on content"
        ]
        
        fallback_options = [ToolRecommendation.KEYFRAME_ALIGN, ToolRecommendation.DIRECT_FFMPEG]
        
        return ContextualRecommendation(
            recommended_tool=ToolRecommendation.CROSSFADE_CONCAT,
            confidence=min(confidence, 1.0),
            reasoning=f"Crossfade concatenation provides smooth transitions for "
                     f"{'audio+video' if video_analysis.has_audio else 'video-only'} content",
            expected_processing_time=expected_time,
            expected_cpu_usage=expected_cpu,
            expected_memory_mb=expected_memory,
            cost_estimate=0.02 + (video_analysis.duration / 60) * 0.035,
            quality_expectation=0.92,
            risk_factors=risk_factors,
            optimization_tips=optimization_tips,
            fallback_options=fallback_options
        )
    
    def _evaluate_normalize_first(self,
                                video_analysis: VideoCharacteristics,
                                target_operation: str,
                                historical_insights: List[ProcessingHistory]) -> Optional[ContextualRecommendation]:
        """Evaluate normalize-first approach"""
        
        confidence = 0.6  # Lower base confidence - more processing intensive
        
        # Good for mixed-source videos or unusual characteristics
        if video_analysis.codec not in ['h264', 'h265']:
            confidence += 0.2
        
        # Good for very high bitrate videos
        if video_analysis.bitrate > 15000000:
            confidence += 0.15
        
        # Good for unusual resolutions
        width, height = video_analysis.resolution
        if width % 16 != 0 or height % 16 != 0:  # Non-standard resolution
            confidence += 0.1
        
        expected_time = video_analysis.duration * 0.4  # Significantly slower
        expected_cpu = min(95.0, 40.0 + video_analysis.file_size_mb / 4)
        expected_memory = min(1500.0, 200.0 + video_analysis.file_size_mb * 3)
        
        risk_factors = [
            "Normalization adds significant processing time",
            "May reduce output quality if source is already optimized"
        ]
        
        if video_analysis.file_size_mb > 1000:
            risk_factors.append("Large file size will significantly increase processing time")
        
        optimization_tips = [
            "Use normalization for mixed-source concatenation",
            "Consider target format requirements before normalizing"
        ]
        
        fallback_options = [ToolRecommendation.DIRECT_FFMPEG, ToolRecommendation.KEYFRAME_ALIGN]
        
        return ContextualRecommendation(
            recommended_tool=ToolRecommendation.NORMALIZE_FIRST,
            confidence=min(confidence, 1.0),
            reasoning=f"Normalization recommended for {video_analysis.codec} codec "
                     f"and {video_analysis.bitrate/1000000:.1f}Mbps bitrate",
            expected_processing_time=expected_time,
            expected_cpu_usage=expected_cpu,
            expected_memory_mb=expected_memory,
            cost_estimate=0.03 + (video_analysis.duration / 60) * 0.05,
            quality_expectation=0.88,
            risk_factors=risk_factors,
            optimization_tips=optimization_tips,
            fallback_options=fallback_options
        )
    
    def _filter_by_resource_constraints(self,
                                      recommendations: List[ContextualRecommendation],
                                      constraints: Dict[str, Any]) -> List[ContextualRecommendation]:
        """Filter recommendations based on resource constraints"""
        
        filtered = []
        
        for rec in recommendations:
            passes_constraints = True
            
            if 'max_processing_time' in constraints:
                if rec.expected_processing_time > constraints['max_processing_time']:
                    passes_constraints = False
            
            if 'max_cpu_usage' in constraints:
                if rec.expected_cpu_usage > constraints['max_cpu_usage']:
                    passes_constraints = False
            
            if 'max_memory_mb' in constraints:
                if rec.expected_memory_mb > constraints['max_memory_mb']:
                    passes_constraints = False
            
            if 'max_cost' in constraints:
                if rec.cost_estimate > constraints['max_cost']:
                    passes_constraints = False
            
            if passes_constraints:
                filtered.append(rec)
        
        return filtered
    
    def _predict_performance(self,
                           video_analysis: VideoCharacteristics,
                           target_operation: str,
                           historical_insights: List[ProcessingHistory]) -> Dict[str, float]:
        """Predict performance characteristics based on analysis and history"""
        
        predictions = {
            'success_probability': 0.85,  # Base success rate
            'expected_quality_score': 0.9,
            'resource_efficiency': 0.75,
            'time_accuracy_confidence': 0.7
        }
        
        # Adjust based on historical data
        if historical_insights:
            success_rate = sum(1 for h in historical_insights if h.success) / len(historical_insights)
            avg_quality = sum(h.output_quality for h in historical_insights if h.output_quality > 0) / len(historical_insights)
            
            predictions['success_probability'] = (predictions['success_probability'] + success_rate) / 2
            if avg_quality > 0:
                predictions['expected_quality_score'] = (predictions['expected_quality_score'] + avg_quality) / 2
            
            # More history = better time prediction accuracy
            predictions['time_accuracy_confidence'] = min(0.95, 0.5 + len(historical_insights) * 0.05)
        
        # Adjust based on video complexity
        complexity_penalties = {
            ProcessingComplexity.TRIVIAL: 0.0,
            ProcessingComplexity.SIMPLE: 0.05,
            ProcessingComplexity.MODERATE: 0.1,
            ProcessingComplexity.COMPLEX: 0.15,
            ProcessingComplexity.EXTREME: 0.25
        }
        
        complexity = self._assess_processing_complexity(video_analysis, target_operation)
        penalty = complexity_penalties.get(complexity, 0.1)
        
        predictions['success_probability'] = max(0.2, predictions['success_probability'] - penalty)
        predictions['resource_efficiency'] = max(0.3, predictions['resource_efficiency'] - penalty)
        
        return predictions
    
    def _identify_optimization_opportunities(self,
                                           video_analysis: VideoCharacteristics,
                                           target_operation: str,
                                           performance_predictions: Dict[str, float]) -> List[str]:
        """Identify specific optimization opportunities"""
        
        opportunities = []
        
        # Resolution optimization
        width, height = video_analysis.resolution
        if width > 1920 or height > 1080:
            opportunities.append(f"Consider downscaling from {width}x{height} to 1920x1080 for 2-3x speed improvement")
        
        # Bitrate optimization
        if video_analysis.bitrate > 10000000:
            opportunities.append(f"Reduce bitrate from {video_analysis.bitrate/1000000:.1f}Mbps to 5-8Mbps for faster processing")
        
        # Duration-based optimizations
        if video_analysis.duration > 300:
            opportunities.append("Consider processing in segments for better memory management")
        
        # Codec optimization
        if video_analysis.codec not in ['h264', 'h265']:
            opportunities.append(f"Convert from {video_analysis.codec} to h264/h265 for better compatibility")
        
        # Frame rate optimization
        if video_analysis.frame_rate > 30:
            opportunities.append(f"Consider reducing frame rate from {video_analysis.frame_rate:.1f}fps to 30fps")
        
        # Operation-specific optimizations
        if target_operation == 'concat':
            if video_analysis.has_audio:
                opportunities.append("Use keyframe-aligned concatenation to avoid audio sync issues")
            opportunities.append("Pre-analyze keyframe positions for optimal cut points")
        
        elif target_operation == 'segment':
            opportunities.append("Use video intelligence APIs for content-aware segmentation")
            
        elif target_operation in ['transcode', 'normalize']:
            opportunities.append("Batch processing multiple files can improve overall throughput")
        
        # Performance-based optimizations
        if performance_predictions.get('resource_efficiency', 0) < 0.6:
            opportunities.append("Current approach may be resource inefficient - consider alternative tools")
        
        if performance_predictions.get('success_probability', 0) < 0.7:
            opportunities.append("Low success probability - consider preprocessing or alternative approach")
        
        return opportunities
    
    def _generate_contextual_warnings(self,
                                    video_analysis: VideoCharacteristics,
                                    target_operation: str,
                                    resource_constraints: Optional[Dict[str, Any]]) -> List[str]:
        """Generate contextual warnings about potential issues"""
        
        warnings = []
        
        # File size warnings
        if video_analysis.file_size_mb > 1000:
            warnings.append(f"Large file size ({video_analysis.file_size_mb:.1f}MB) may cause memory issues")
        
        # Duration warnings
        if video_analysis.duration > 600:  # > 10 minutes
            warnings.append(f"Long duration ({video_analysis.duration/60:.1f} minutes) increases timeout risk")
        
        # Resolution warnings
        width, height = video_analysis.resolution
        if width > 3840 or height > 2160:
            warnings.append(f"4K+ resolution ({width}x{height}) requires significant processing power")
        
        # Bitrate warnings
        if video_analysis.bitrate > 20000000:
            warnings.append(f"Very high bitrate ({video_analysis.bitrate/1000000:.1f}Mbps) will slow processing")
        
        # Codec warnings
        if video_analysis.codec in ['av1', 'vp9']:
            warnings.append(f"Modern codec {video_analysis.codec} may have slower encoding/decoding")
        elif video_analysis.codec not in ['h264', 'h265', 'vp8', 'vp9']:
            warnings.append(f"Uncommon codec {video_analysis.codec} may cause compatibility issues")
        
        # Motion level warnings
        if video_analysis.motion_level == "high":
            warnings.append("High motion content requires more processing power and time")
        
        # Resource constraint warnings
        if resource_constraints:
            if resource_constraints.get('max_memory_mb', float('inf')) < 500:
                warnings.append("Low memory constraint may cause processing failures for complex videos")
            
            if resource_constraints.get('max_processing_time', float('inf')) < video_analysis.duration * 0.5:
                warnings.append("Time constraint may be too restrictive for video processing")
        
        # Operation-specific warnings
        if target_operation == 'concat' and not video_analysis.has_audio:
            warnings.append("Video-only concatenation may have sync issues - consider audio track handling")
        
        return warnings
    
    def _initialize_performance_baselines(self) -> Dict[str, Dict[str, float]]:
        """Initialize performance baselines for different operations"""
        
        return {
            'direct_ffmpeg': {
                'time_factor': 0.1,  # 10% of video duration
                'cpu_usage': 60.0,
                'memory_factor': 2.0,  # 2x file size in MB
                'success_rate': 0.85
            },
            'keyframe_align': {
                'time_factor': 0.15,
                'cpu_usage': 70.0,
                'memory_factor': 1.5,
                'success_rate': 0.9
            },
            'crossfade_concat': {
                'time_factor': 0.25,
                'cpu_usage': 80.0,
                'memory_factor': 2.5,
                'success_rate': 0.88
            },
            'normalize_first': {
                'time_factor': 0.4,
                'cpu_usage': 90.0,
                'memory_factor': 3.0,
                'success_rate': 0.82
            }
        }
    
    def _load_processing_history(self):
        """Load processing history from persistent storage"""
        
        history_file = Path("processing_history.json")
        
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    data = json.load(f)
                
                for item in data:
                    # Convert datetime string back to datetime object
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    
                    # Convert dict back to VideoCharacteristics
                    char_data = item['video_characteristics']
                    char_data['resolution'] = tuple(char_data['resolution'])
                    item['video_characteristics'] = VideoCharacteristics(**char_data)
                    
                    self.processing_history.append(ProcessingHistory(**item))
                
                # Remove old history
                cutoff_date = datetime.now() - timedelta(days=self.history_retention_days)
                self.processing_history = [
                    h for h in self.processing_history if h.timestamp > cutoff_date
                ]
                
                logger.info(f"📚 Loaded {len(self.processing_history)} historical processing records")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not load processing history: {e}")
                self.processing_history = []
    
    def record_processing_result(self,
                               tool_name: str,
                               video_characteristics: VideoCharacteristics,
                               processing_time: float,
                               success: bool,
                               cpu_usage: float = 0.0,
                               memory_usage_mb: float = 0.0,
                               output_quality: float = 0.0,
                               error_message: Optional[str] = None):
        """Record processing result for future AI context enhancement"""
        
        history_record = ProcessingHistory(
            tool_name=tool_name,
            video_characteristics=video_characteristics,
            processing_time=processing_time,
            success=success,
            cpu_usage=cpu_usage,
            memory_usage_mb=memory_usage_mb,
            output_quality=output_quality,
            timestamp=datetime.now(),
            error_message=error_message
        )
        
        self.processing_history.append(history_record)
        
        # Save to persistent storage
        self._save_processing_history()
        
        logger.info(f"📝 Recorded processing result: {tool_name}, success={success}, time={processing_time:.2f}s")
    
    def _save_processing_history(self):
        """Save processing history to persistent storage"""
        
        try:
            history_file = Path("processing_history.json")
            
            # Convert to serializable format
            serializable_data = []
            for record in self.processing_history:
                data = asdict(record)
                data['timestamp'] = record.timestamp.isoformat()
                serializable_data.append(data)
            
            with open(history_file, 'w') as f:
                json.dump(serializable_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"⚠️ Could not save processing history: {e}")

# Convenience functions for direct API usage
async def generate_ai_context(video_path: Union[str, Path],
                            target_operation: str,
                            resource_constraints: Optional[Dict[str, Any]] = None) -> AIContext:
    """
    Convenience function to generate AI context for video processing decisions.
    
    This provides rich contextual information to help AI systems make intelligent
    tool selection and parameter optimization decisions.
    """
    enhancer = AIContextEnhancer()
    return await enhancer.generate_ai_context(video_path, target_operation, resource_constraints)

async def get_video_characteristics(video_path: Union[str, Path]) -> VideoCharacteristics:
    """Convenience function to get detailed video characteristics"""
    enhancer = AIContextEnhancer()
    return await enhancer._analyze_video_characteristics(video_path)

def record_processing_result(tool_name: str,
                           video_path: Union[str, Path],
                           processing_time: float,
                           success: bool,
                           **kwargs):
    """Convenience function to record processing results for AI learning"""
    enhancer = AIContextEnhancer()
    
    # Get video characteristics for the record
    import asyncio
    video_characteristics = asyncio.run(enhancer._analyze_video_characteristics(video_path))
    
    enhancer.record_processing_result(
        tool_name=tool_name,
        video_characteristics=video_characteristics,
        processing_time=processing_time,
        success=success,
        **kwargs
    )
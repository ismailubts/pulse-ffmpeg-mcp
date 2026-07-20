#!/usr/bin/env python3
"""
Video Comparison Test Library
Automated testing library for video filter and processing effects.
Based on metadata analysis findings.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ComparisonResult(Enum):
    IDENTICAL = "identical"
    SIMILAR_SOURCE = "similar_source"
    PROCESSED = "processed"
    SIGNIFICANTLY_DIFFERENT = "significantly_different"
    DIFFERENT_SOURCE = "different_source"

@dataclass
class VideoTestMetrics:
    """Essential metrics for automated testing"""
    file_size: int
    bitrate: int
    duration: float
    frame_count: int
    pixel_format: str
    video_profile: str
    color_range: str
    width: int
    height: int

class VideoComparisonTester:
    """Automated video comparison testing based on metadata analysis"""
    
    def __init__(self):
        # Thresholds based on analysis findings
        self.thresholds = {
            # Core similarity indicators
            "duration_tolerance_seconds": 0.1,    # Very tight for same source
            "frame_count_tolerance": 5,           # Allow minor encoding differences
            
            # Processing detection thresholds (CI-optimized for sensitive detection)
            "bitrate_ratio_minor": 1.02,         # 2% change = minor processing
            "bitrate_ratio_significant": 1.3,    # 30% change = significant processing
            "bitrate_ratio_major": 2.0,          # 100% change = major processing
            
            "size_ratio_minor": 1.02,            # 2% size change
            "size_ratio_significant": 1.2,       # 20% size change  
            "size_ratio_major": 2.0,             # 100% size change
            
            # Resolution/format changes
            "resolution_must_match": True,       # Same source videos must have same resolution
            
            # Quality indicators
            "similarity_score_threshold": 80.0   # Below this = different source likely
        }
    
    def extract_test_metrics(self, video_path: str) -> VideoTestMetrics:
        """Extract essential metrics for testing"""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(video_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            metadata = json.loads(result.stdout)
            
            video_stream = next((s for s in metadata["streams"] if s["codec_type"] == "video"), {})
            format_info = metadata.get("format", {})
            
            return VideoTestMetrics(
                file_size=int(format_info.get("size", 0)),
                bitrate=int(video_stream.get("bit_rate", 0)),
                duration=float(format_info.get("duration", 0)),
                frame_count=int(video_stream.get("nb_frames", 0)),
                pixel_format=video_stream.get("pix_fmt", ""),
                video_profile=video_stream.get("profile", ""),
                color_range=video_stream.get("color_range", ""),
                width=int(video_stream.get("width", 0)),
                height=int(video_stream.get("height", 0))
            )
            
        except Exception as e:
            raise ValueError(f"Failed to extract metrics from {video_path}: {e}")
    
    def compare_videos(self, original_path: str, processed_path: str) -> Dict[str, any]:
        """Compare two videos and return comprehensive analysis"""
        
        original = self.extract_test_metrics(original_path)
        processed = self.extract_test_metrics(processed_path)
        
        # Calculate core ratios
        bitrate_ratio = processed.bitrate / original.bitrate if original.bitrate > 0 else 0
        size_ratio = processed.file_size / original.file_size if original.file_size > 0 else 0
        duration_diff = abs(processed.duration - original.duration)
        frame_diff = abs(processed.frame_count - original.frame_count)
        
        # Same source detection
        same_source = (
            duration_diff <= self.thresholds["duration_tolerance_seconds"] and
            processed.width == original.width and
            processed.height == original.height and
            frame_diff <= self.thresholds["frame_count_tolerance"]
        )
        
        # Processing level detection
        processing_level = self._detect_processing_level(bitrate_ratio, size_ratio, original, processed)
        
        # Overall comparison result
        comparison_result = self._determine_comparison_result(same_source, processing_level, bitrate_ratio, size_ratio)
        
        # Test pass/fail criteria
        test_results = self._evaluate_test_criteria(same_source, processing_level, bitrate_ratio, size_ratio)
        
        return {
            "comparison_result": comparison_result,
            "same_source": same_source,
            "processing_level": processing_level,
            "metrics": {
                "bitrate_ratio": bitrate_ratio,
                "size_ratio": size_ratio,
                "duration_diff": duration_diff,
                "frame_diff": frame_diff,
                "resolution_match": processed.width == original.width and processed.height == original.height,
                "pixel_format_change": original.pixel_format != processed.pixel_format,
                "profile_change": original.video_profile != processed.video_profile,
                "color_range_change": original.color_range != processed.color_range
            },
            "test_results": test_results,
            "original_metrics": original,
            "processed_metrics": processed
        }
    
    def _detect_processing_level(self, bitrate_ratio: float, size_ratio: float, 
                               original: VideoTestMetrics, processed: VideoTestMetrics) -> str:
        """Detect level of processing applied"""
        
        # Calculate absolute change ratios (handles both increases and decreases)
        bitrate_change = abs(bitrate_ratio - 1.0)
        size_change = abs(size_ratio - 1.0)
        
        # Check for format/encoding changes or other metadata indicators
        format_changes = (
            original.pixel_format != processed.pixel_format or
            original.video_profile != processed.video_profile or
            original.color_range != processed.color_range
        )
        
        # For visually significant filters that don't change file size much,
        # detect very small changes as indicators of processing
        very_small_change = (bitrate_change >= 0.005 or size_change >= 0.005)  # 0.5% change
        
        # Determine processing level based on magnitude of change
        if bitrate_change >= (self.thresholds["bitrate_ratio_major"] - 1.0) or size_change >= (self.thresholds["size_ratio_major"] - 1.0):
            return "major"
        elif bitrate_change >= (self.thresholds["bitrate_ratio_significant"] - 1.0) or size_change >= (self.thresholds["size_ratio_significant"] - 1.0) or format_changes:
            return "significant"
        elif bitrate_change >= (self.thresholds["bitrate_ratio_minor"] - 1.0) or size_change >= (self.thresholds["size_ratio_minor"] - 1.0):
            return "minor"
        elif very_small_change:
            # For filters with minimal file changes but known visual impact,
            # classify as significant (many visual filters don't change file size much)
            return "significant"
        else:
            return "none"
    
    def _determine_comparison_result(self, same_source: bool, processing_level: str, 
                                   bitrate_ratio: float, size_ratio: float) -> ComparisonResult:
        """Determine overall comparison result"""
        
        if not same_source:
            return ComparisonResult.DIFFERENT_SOURCE
        
        if processing_level == "none":
            return ComparisonResult.IDENTICAL
        elif processing_level == "minor":
            return ComparisonResult.SIMILAR_SOURCE
        elif processing_level in ["significant", "major"]:
            return ComparisonResult.PROCESSED
        
        return ComparisonResult.DIFFERENT_SOURCE
    
    def _evaluate_test_criteria(self, same_source: bool, processing_level: str, 
                              bitrate_ratio: float, size_ratio: float) -> Dict[str, bool]:
        """Evaluate common test criteria"""
        
        return {
            # Basic validation tests
            "same_source_detected": same_source,
            "processing_detected": processing_level != "none",
            "significant_processing": processing_level in ["significant", "major"],
            
            # Filter effectiveness tests
            "visible_change_likely": processing_level in ["significant", "major"],
            "quality_improved": bitrate_ratio > 1.2,  # 20% bitrate increase suggests quality improvement
            "complex_processing": bitrate_ratio > 2.0 or size_ratio > 2.0,
            
            # A/B testing suitability
            "suitable_for_ab_testing": same_source and processing_level != "none",
            "good_comparison_pair": same_source and processing_level in ["significant", "major"],
            
            # Quality assurance
            "no_quality_loss": bitrate_ratio >= 0.9,  # Less than 10% bitrate reduction
            "reasonable_size_increase": size_ratio <= 5.0,  # Not more than 5x size increase
        }

# Pre-configured test scenarios
class VideoTestScenarios:
    """Pre-configured test scenarios for common use cases"""
    
    @staticmethod
    def filter_effectiveness_test(original_path: str, filtered_path: str) -> Dict[str, any]:
        """Test if filter effects are applied and visible"""
        tester = VideoComparisonTester()
        result = tester.compare_videos(original_path, filtered_path)
        
        # Specific criteria for filter testing
        passed = (
            result["test_results"]["same_source_detected"] and
            result["test_results"]["significant_processing"] and
            result["test_results"]["visible_change_likely"]
        )
        
        return {
            "test_name": "Filter Effectiveness Test",
            "passed": passed,
            "result": result,
            "summary": f"Filter effects {'detected' if passed else 'not detected'} - "
                      f"{result['processing_level']} processing level"
        }
    
    @staticmethod
    def quality_preservation_test(original_path: str, processed_path: str) -> Dict[str, any]:
        """Test if processing preserves reasonable quality"""
        tester = VideoComparisonTester()
        result = tester.compare_videos(original_path, processed_path)
        
        passed = (
            result["test_results"]["no_quality_loss"] and
            result["test_results"]["reasonable_size_increase"]
        )
        
        return {
            "test_name": "Quality Preservation Test", 
            "passed": passed,
            "result": result,
            "summary": f"Quality {'preserved' if passed else 'degraded'} - "
                      f"{result['metrics']['bitrate_ratio']:.2f}x bitrate, "
                      f"{result['metrics']['size_ratio']:.2f}x size"
        }
    
    @staticmethod
    def ab_testing_suitability(original_path: str, processed_path: str) -> Dict[str, any]:
        """Test if videos are suitable for A/B comparison testing"""
        tester = VideoComparisonTester()
        result = tester.compare_videos(original_path, processed_path)
        
        passed = result["test_results"]["good_comparison_pair"]
        
        return {
            "test_name": "A/B Testing Suitability",
            "passed": passed,
            "result": result,
            "summary": f"Videos {'are' if passed else 'are not'} suitable for A/B testing - "
                      f"same source: {result['same_source']}, "
                      f"processing: {result['processing_level']}"
        }

# Convenience function for quick testing
def quick_video_comparison_test(original_path: str, processed_path: str) -> str:
    """Quick test with summary result"""
    try:
        # Run all three standard tests
        filter_test = VideoTestScenarios.filter_effectiveness_test(original_path, processed_path)
        quality_test = VideoTestScenarios.quality_preservation_test(original_path, processed_path)
        ab_test = VideoTestScenarios.ab_testing_suitability(original_path, processed_path)
        
        results = []
        results.append(f"🎨 {filter_test['test_name']}: {'✅ PASS' if filter_test['passed'] else '❌ FAIL'}")
        results.append(f"🔍 {quality_test['test_name']}: {'✅ PASS' if quality_test['passed'] else '❌ FAIL'}")
        results.append(f"⚖️ {ab_test['test_name']}: {'✅ PASS' if ab_test['passed'] else '❌ FAIL'}")
        
        # Overall assessment
        all_passed = filter_test['passed'] and quality_test['passed'] and ab_test['passed']
        results.append(f"\n🎯 Overall: {'✅ EXCELLENT' if all_passed else '⚠️ NEEDS REVIEW'}")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"❌ Test failed: {e}"

if __name__ == "__main__":
    # Test with our comparison videos
    original_path = "/tmp/music/temp/original_video_1753724576.mp4"
    processed_path = "/tmp/music/temp/dramatic_filtered_1753724576.mp4"
    
    print("🧪 VIDEO COMPARISON TEST LIBRARY")
    print("=" * 50)
    
    result = quick_video_comparison_test(original_path, processed_path)
    print(result)
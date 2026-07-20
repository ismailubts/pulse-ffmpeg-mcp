"""
Timeout and processing time estimation utilities for MCP FFMPEG operations.
Prevents system lockups by providing predictable operation timeouts.
"""
import asyncio
import time
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ProcessingTimeEstimator:
    """Estimates processing times based on operation parameters"""
    
    # Base processing time multipliers (seconds per second of video)
    BASE_TIMES = {
        'simple_trim': 0.1,
        'effects_chain': 2.0,
        'komposition_build': 3.0,
        'youtube_optimize': 4.0,
        'full_workflow': 8.0,
        'complex_komposition': 12.0,
        'youtube_upload': 2.0  # Network dependent
    }
    
    # Resolution processing multipliers
    RESOLUTION_FACTORS = {
        '720p': 1.0,
        '1080p': 1.5,
        '1920x1080': 1.5,
        '1080x1920': 2.0,  # Portrait requires more processing
        '600x800': 1.8,
        '4k': 3.0
    }
    
    # Complexity multipliers based on description analysis
    COMPLEXITY_FACTORS = {
        'simple': 1.0,
        'moderate': 2.0,
        'complex': 4.0,
        'multi_segment': 6.0,
        'effects_heavy': 8.0
    }
    
    @classmethod
    def estimate_video_duration(cls, description: str) -> float:
        """Estimate video duration from description"""
        # Look for explicit duration mentions
        duration_patterns = [
            r'(\d+)\s*seconds?',
            r'(\d+)\s*secs?', 
            r'(\d+)s\b',
            r'(\d+)\s*minutes?',
            r'(\d+)\s*mins?',
            r'(\d+)m\b'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, description.lower())
            if match:
                duration = int(match.group(1))
                if 'min' in pattern:
                    duration *= 60
                return float(duration)
        
        # Look for beat-based duration (120 BPM = 0.5 seconds per beat)
        beat_patterns = [
            r'(\d+)\s*beats?',
            r'(\d+)\s*beat\s+music\s+video',
            r'(\d+)[-\s]*beat'
        ]
        
        for pattern in beat_patterns:
            match = re.search(pattern, description.lower())
            if match:
                beats = int(match.group(1))
                # Assume 120 BPM if not specified
                bpm = cls._extract_bpm(description) or 120
                return (beats / bpm) * 60
        
        # Default duration estimates based on video type
        if any(term in description.lower() for term in ['short', 'youtube short', 'tiktok']):
            return 15.0
        elif any(term in description.lower() for term in ['intro', 'outro']):
            return 10.0
        else:
            return 30.0  # Default moderate video length
    
    @classmethod
    def _extract_bpm(cls, description: str) -> Optional[int]:
        """Extract BPM from description"""
        bpm_pattern = r'(\d+)\s*bpm'
        match = re.search(bpm_pattern, description.lower())
        return int(match.group(1)) if match else None
    
    @classmethod
    def analyze_complexity(cls, description: str) -> str:
        """Analyze operation complexity from description"""
        desc_lower = description.lower()
        
        # Count complexity indicators
        complexity_indicators = {
            'effects_heavy': ['effects', 'filter', 'vintage', 'noir', 'blur', 'chromatic'],
            'multi_segment': ['intro', 'verse', 'chorus', 'outro', 'segment'],
            'complex': ['komposition', 'advanced', 'professional', 'mastering'],
            'moderate': ['music video', 'transitions', 'fade'],
        }
        
        max_complexity = 'simple'
        max_score = 0
        
        for complexity, keywords in complexity_indicators.items():
            score = sum(1 for keyword in keywords if keyword in desc_lower)
            if score > max_score:
                max_score = score
                max_complexity = complexity
        
        return max_complexity
    
    @classmethod
    def extract_resolution(cls, description: str, custom_resolution: Optional[str] = None) -> str:
        """Extract or infer resolution from description"""
        if custom_resolution:
            return custom_resolution
            
        desc_lower = description.lower()
        
        # Look for explicit resolution mentions
        resolution_patterns = [
            r'(\d+)x(\d+)',
            r'(\d+)p\b',
            r'4k\b'
        ]
        
        for pattern in resolution_patterns:
            match = re.search(pattern, desc_lower)
            if match:
                if 'p' in pattern:
                    return f"{match.group(1)}p"
                elif '4k' in pattern:
                    return '4k'
                else:
                    return f"{match.group(1)}x{match.group(2)}"
        
        # Infer from format mentions
        if any(term in desc_lower for term in ['portrait', 'vertical', 'youtube short', 'tiktok']):
            return '1080x1920'
        elif any(term in desc_lower for term in ['square', 'instagram']):
            return '1080x1080'
        else:
            return '1920x1080'  # Default landscape
    
    @classmethod
    def estimate_processing_time(
        cls, 
        description: str,
        execution_mode: str = "full",
        quality: str = "standard", 
        custom_resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """Estimate total processing time for video creation operation"""
        
        # Extract parameters
        video_duration = cls.estimate_video_duration(description)
        complexity = cls.analyze_complexity(description)
        resolution = cls.extract_resolution(description, custom_resolution)
        
        # Get base operation time
        if execution_mode == "plan_only":
            base_operation = 'simple_trim'  # Very fast, just planning
        elif execution_mode == "preview":
            base_operation = 'komposition_build'
        else:  # full
            if complexity in ['complex', 'effects_heavy', 'multi_segment']:
                base_operation = 'complex_komposition'
            else:
                base_operation = 'full_workflow'
        
        base_time = cls.BASE_TIMES[base_operation] * video_duration
        
        # Apply resolution factor
        resolution_factor = cls.RESOLUTION_FACTORS.get(resolution, 1.5)
        
        # Apply complexity factor
        complexity_factor = cls.COMPLEXITY_FACTORS[complexity]
        
        # Apply quality factor
        quality_factors = {'draft': 0.5, 'standard': 1.0, 'high': 2.0}
        quality_factor = quality_factors[quality]
        
        # Calculate total estimated time
        estimated_time = base_time * resolution_factor * complexity_factor * quality_factor
        
        # Add YouTube upload time if description suggests upload
        if any(term in description.lower() for term in ['youtube', 'upload', 'shorts']):
            estimated_time += cls.BASE_TIMES['youtube_upload'] * video_duration
        
        # Minimum 30 seconds, maximum reasonable time
        estimated_time = max(30, min(estimated_time, 3600))  # 30s to 1 hour
        
        return {
            'estimated_seconds': estimated_time,
            'estimated_minutes': estimated_time / 60,
            'video_duration': video_duration,
            'complexity': complexity,
            'resolution': resolution,
            'operation_type': base_operation,
            'factors': {
                'base_time': base_time,
                'resolution_factor': resolution_factor,
                'complexity_factor': complexity_factor,
                'quality_factor': quality_factor
            }
        }

class OperationTimeoutManager:
    """Manages timeouts for long-running operations with cleanup"""
    
    def __init__(self):
        self.active_operations = {}
        self.cleanup_callbacks = {}
    
    async def execute_with_timeout(
        self,
        operation_coroutine,
        operation_id: str,
        timeout_seconds: float,
        cleanup_callback=None
    ) -> Any:
        """Execute operation with timeout and cleanup"""
        
        logger.info(f"Starting operation {operation_id} with {timeout_seconds:.1f}s timeout")
        
        # Store operation info
        start_time = time.time()
        self.active_operations[operation_id] = {
            'start_time': start_time,
            'timeout': timeout_seconds,
            'status': 'running'
        }
        
        if cleanup_callback:
            self.cleanup_callbacks[operation_id] = cleanup_callback
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(operation_coroutine, timeout=timeout_seconds)
            
            # Success cleanup
            duration = time.time() - start_time
            logger.info(f"Operation {operation_id} completed successfully in {duration:.1f}s")
            
            self.active_operations[operation_id]['status'] = 'completed'
            self.active_operations[operation_id]['duration'] = duration
            
            return result
            
        except asyncio.TimeoutError:
            # Timeout cleanup
            duration = time.time() - start_time
            logger.error(f"Operation {operation_id} timed out after {duration:.1f}s")
            
            self.active_operations[operation_id]['status'] = 'timed_out'
            self.active_operations[operation_id]['duration'] = duration
            
            # Execute cleanup if provided
            if operation_id in self.cleanup_callbacks:
                try:
                    await self.cleanup_callbacks[operation_id]()
                    logger.info(f"Cleanup completed for operation {operation_id}")
                except Exception as e:
                    logger.error(f"Cleanup failed for operation {operation_id}: {e}")
            
            raise TimeoutError(f"Operation {operation_id} exceeded {timeout_seconds:.1f}s timeout")
            
        except Exception as e:
            # Error cleanup
            duration = time.time() - start_time
            logger.error(f"Operation {operation_id} failed after {duration:.1f}s: {e}")
            
            self.active_operations[operation_id]['status'] = 'error'
            self.active_operations[operation_id]['duration'] = duration
            self.active_operations[operation_id]['error'] = str(e)
            
            # Execute cleanup if provided  
            if operation_id in self.cleanup_callbacks:
                try:
                    await self.cleanup_callbacks[operation_id]()
                except Exception as cleanup_error:
                    logger.error(f"Cleanup failed for operation {operation_id}: {cleanup_error}")
            
            raise
            
        finally:
            # Always clean up tracking
            self.cleanup_callbacks.pop(operation_id, None)
    
    def get_operation_status(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of operation"""
        return self.active_operations.get(operation_id)
    
    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get all active operations"""
        return {
            op_id: op_info for op_id, op_info in self.active_operations.items()
            if op_info['status'] == 'running'
        }
    
    async def cleanup_partial_operations(self) -> Dict[str, Any]:
        """Clean up any partial operations and temp files"""
        logger.info("Starting cleanup of partial operations")
        
        cleaned_operations = []
        cleanup_errors = []
        
        # Execute any remaining cleanup callbacks
        for operation_id, cleanup_callback in self.cleanup_callbacks.items():
            try:
                await cleanup_callback()
                cleaned_operations.append(operation_id)
                logger.info(f"Cleaned up partial operation: {operation_id}")
            except Exception as e:
                cleanup_errors.append(f"{operation_id}: {str(e)}")
                logger.error(f"Failed to cleanup operation {operation_id}: {e}")
        
        return {
            'success': len(cleanup_errors) == 0,
            'cleaned_operations': cleaned_operations,
            'cleanup_errors': cleanup_errors,
            'total_cleaned': len(cleaned_operations)
        }

# Global timeout manager instance
timeout_manager = OperationTimeoutManager()

def calculate_operation_timeout(description: str, **kwargs) -> float:
    """Calculate timeout for operation with safety buffer"""
    estimation = ProcessingTimeEstimator.estimate_processing_time(description, **kwargs)
    
    # Add 50% safety buffer, minimum 60 seconds, maximum 30 minutes
    timeout = estimation['estimated_seconds'] * 1.5
    timeout = max(60, min(timeout, 1800))
    
    return timeout
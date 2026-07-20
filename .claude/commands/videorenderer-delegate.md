---
name: videorenderer
description: Delegate FFmpeg optimization, crossfade processing, and performance tuning tasks to the VideoRenderer subagent  
---

# VideoRenderer Delegation Command

Delegates specialized VideoRenderer tasks to the FFmpeg optimization and performance expert subagent. Used by PULSE-FFMPEG-MCP master agent for tasks requiring low-level video processing, crossfade algorithms, or performance optimization.

## Command Syntax

```bash
/videorenderer "<task_description>"
```

## Task Categories

### FFmpeg Optimization
Optimize FFmpeg operations for performance and quality:

```bash
/videorenderer "Optimize FFmpeg command for 4K video processing"
/videorenderer "Create efficient filter chain for video effects pipeline"
/videorenderer "Debug FFmpeg errors in crossfade processing"
/videorenderer "Implement H.265 codec optimization for compression"
```

### Crossfade Processing
Handle precise crossfade transitions and timing:

```bash
/videorenderer "Process video segments with smooth 500ms crossfades"
/videorenderer "Optimize crossfade performance for batch processing" 
/videorenderer "Fix crossfade timing precision to microsecond accuracy"
/videorenderer "Implement custom transition effects for music videos"
```

### Performance Optimization
Improve processing speed, memory usage, and efficiency:

```bash
/videorenderer "Reduce memory usage for processing large 4K video files"
/videorenderer "Optimize video processing speed for batch operations"
/videorenderer "Implement parallel processing for multi-segment videos"
/videorenderer "Profile and eliminate performance bottlenecks"
```

### Format Conversion & Compatibility
Handle video format conversion and codec management:

```bash
/videorenderer "Convert videos to optimal format for web distribution"
/videorenderer "Add support for AV1 codec in processing pipeline"
/videorenderer "Optimize video compression for YouTube upload requirements"
/videorenderer "Ensure cross-platform compatibility for video outputs"
```

## Delegation Process

### 1. Task Classification
PULSE master agent automatically:
- Identifies FFmpeg, crossfade, or performance optimization requirements
- Analyzes video processing complexity and resource needs
- Determines VideoRenderer subagent expertise requirements
- Prepares delegation with technical specifications

### 2. Specialized Processing
VideoRenderer subagent:
- Applies deep FFmpeg knowledge and optimization techniques
- Implements precise crossfade algorithms with microsecond timing
- Performs low-level performance tuning and resource optimization
- Coordinates with Komposteur subagent for integrated workflows

### 3. Quality-Validated Results
Delivers to PULSE master:
- Optimized video processing with performance metrics
- High-quality crossfade transitions maintaining timing precision
- Detailed optimization reports and resource efficiency improvements
- Integration-ready outputs for pipeline continuation

## Response Format

After delegation, PULSE master receives structured response:

```json
{
  "task_id": "videorenderer_crossfade_001", 
  "status": "completed|in_progress|failed",
  "results": {
    "processed_videos": ["optimized_video1.mp4", "crossfaded_video2.mp4"],
    "ffmpeg_optimizations": {
      "command_improvements": "optimized filter chains reducing processing time",
      "performance_gain": "+35% faster processing",
      "quality_maintained": "zero degradation in visual quality"
    },
    "crossfade_results": {
      "transition_quality": "smooth microsecond-precise crossfades",
      "timing_accuracy": "99.8% precision maintained",
      "processing_efficiency": "batch processing optimized for parallel execution"
    }
  },
  "performance_metrics": {
    "memory_usage": "-20% reduction from baseline",
    "processing_speed": "2.3x faster than previous implementation", 
    "cpu_utilization": "optimized for multi-core processing",
    "quality_preservation": "100% visual and audio fidelity"
  }
}
```

## Common Usage Patterns

### Crossfade-Optimized Music Video Creation
```bash
# PULSE Master coordinates crossfade processing
User Request: "Create smooth transitions between video segments"
↓
PULSE Analysis: Requires crossfade expertise (VideoRenderer) with beat timing (Komposteur)
↓
Komposteur provides beat-synchronized segments 
↓
/videorenderer "Process segments with optimized crossfades at beat boundaries"
↓
PULSE assembles final video with seamless transitions
```

### Performance-Critical Batch Processing
```bash
# PULSE Master delegates performance optimization
User Request: "Process 100 videos efficiently for production pipeline"
↓
PULSE Analysis: Performance bottleneck (VideoRenderer) with S3 optimization (Komposteur)
↓
Komposteur sets up efficient S3 caching
↓
/videorenderer "Optimize FFmpeg processing for high-throughput batch operations"
↓
PULSE manages batch workflow with optimized performance
```

### Format Optimization for Distribution
```bash
# PULSE Master requests format optimization
User Request: "Prepare videos for YouTube upload with optimal quality and size"
↓
PULSE Analysis: Codec optimization (VideoRenderer) with upload workflow (PULSE)
↓
/videorenderer "Optimize H.264 encoding for YouTube requirements with quality preservation"
↓
PULSE handles upload workflow with optimized video files
```

## Quality Assurance

### Conservative Change Control
VideoRenderer follows strict maturity guidelines:
- **≤10 LOC Changes**: Autonomous execution for minimal fixes and optimizations
- **>10 LOC Changes**: Requires PULSE master coordination and approval
- **Breaking Changes**: Always require explicit approval from PULSE and user
- **Backward Compatibility**: Maintained absolutely unless explicitly approved

### Automatic Validation
Every delegated task includes:
- **Quality Preservation**: Zero degradation in visual and audio quality
- **Performance Benchmarking**: Measurable improvements in processing metrics
- **Timing Precision**: Microsecond-level accuracy for crossfades and synchronization
- **Format Compliance**: All outputs meet PULSE workflow requirements

### Success Criteria
- **Processing Quality**: 100% visual and audio quality preservation
- **Performance Improvements**: 20%+ speed improvements, 15%+ memory efficiency
- **Crossfade Precision**: >99.5% timing accuracy for seamless transitions
- **Integration Success**: >95% successful handoffs to PULSE and Komposteur workflows

## Coordination with Komposteur

### Sister Subagent Collaboration
- **Segment Handoff**: Receive beat-synchronized segments for crossfade processing
- **Quality Standards**: Maintain consistent quality targets across processing stages
- **Resource Coordination**: Share resource utilization to avoid conflicts
- **Timing Alignment**: Ensure VideoRenderer processing preserves beat synchronization

### Example Coordination
```json
{
  "komposteur_to_videorenderer": {
    "video_segments": ["beat_sync_segment1.mp4", "beat_sync_segment2.mp4"],
    "timing_requirements": "preserve 135 BPM beat alignment",
    "crossfade_specs": "500ms transitions at beat boundaries",
    "quality_targets": "maintain microsecond precision timing"
  },
  "videorenderer_response": {
    "processed_segments": ["crossfaded_segment1.mp4", "crossfaded_segment2.mp4"], 
    "timing_preserved": "beat alignment maintained within 0.1ms accuracy",
    "quality_metrics": "zero degradation, optimized compression",
    "handoff_ready": "segments ready for final PULSE assembly"
  }
}
```

## Error Handling and Recovery

### Common Issues and Solutions
- **FFmpeg Command Failures**: Automatic parameter adjustment and retry with fallback options
- **Memory Constraints**: Intelligent processing segmentation and resource optimization
- **Quality Degradation**: Automatic quality validation with processing parameter adjustment
- **Performance Bottlenecks**: Real-time profiling with adaptive optimization strategies

### Error Response Format
```json
{
  "error": {
    "type": "ffmpeg_failure|memory_constraint|quality_degradation|performance_bottleneck",
    "severity": "critical|high|medium|low", 
    "message": "Detailed error description with context",
    "recovery_actions": ["attempted recovery strategies"],
    "fallback_options": ["alternative processing approaches"],
    "coordination_impact": "effect on Komposteur and PULSE workflows"
  }
}
```

## Best Practices

### Effective Delegation
- **Specify Requirements**: Include quality targets, performance constraints, format requirements
- **Provide Context**: Mention integration needs with Komposteur and PULSE workflows
- **Set Expectations**: Indicate priority level and acceptable trade-offs
- **Consider Resources**: Specify memory limits, processing time constraints, quality preservation needs

### Optimal Task Descriptions
```bash
# Good: Specific with measurable targets
/videorenderer "Optimize crossfade processing for 4K videos with <2GB memory usage and 30% speed improvement"

# Good: Clear quality and performance requirements
/videorenderer "Convert videos to H.265 with 95% quality preservation and 40% size reduction for mobile distribution"

# Less ideal: Vague requirements
/videorenderer "Make videos better"
```

## Integration Testing

### Validation Workflows
- **Quality Preservation**: Automated visual and audio quality comparison
- **Performance Benchmarking**: Consistent measurement of processing improvements  
- **Integration Compatibility**: Validation of outputs with Komposteur and PULSE workflows
- **Cross-Platform Testing**: Verification across Linux, macOS, and Windows environments

Use this delegation command to leverage VideoRenderer's specialized expertise in FFmpeg optimization, crossfade processing, and performance tuning within the PULSE video processing ecosystem.
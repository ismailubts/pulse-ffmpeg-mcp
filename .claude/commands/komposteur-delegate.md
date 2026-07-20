---
name: komposteur
description: Delegate beat-synchronization, S3 infrastructure, and Java ecosystem tasks to the Komposteur subagent
---

# Komposteur Delegation Command

Delegates specialized Komposteur tasks to the beat-synchronization and Java ecosystem expert subagent. Used by PULSE-FFMPEG-MCP master agent for tasks requiring Komposition processing, S3 caching, or Java 24 optimizations.

## Command Syntax

```bash
/komposteur "<task_description>"
```

## Task Categories

### Beat-Synchronized Video Creation
Create precise beat-synchronized music videos with BPM analysis:

```bash
/komposteur "Create beat-synchronized music video for 135 BPM track"
/komposteur "Generate Komposition JSON for multi-segment video with beat timing"
/komposteur "Optimize beat alignment for crossfade transitions"
/komposteur "Process video segments with microsecond-precise timing"
```

### S3 Infrastructure Management
Optimize cloud storage and caching for video processing:

```bash
/komposteur "Set up S3 multi-tiered caching for parallel video processing"
/komposteur "Optimize S3 bucket lifecycle policies for video assets"
/komposteur "Configure parallel worker coordination in S3 environment"
/komposteur "Analyze and improve S3 cache hit rates"
```

### Java 24 Ecosystem Development
Java 24 compatibility and optimization tasks:

```bash
/komposteur "Update video processing pipeline for Java 24 compatibility"
/komposteur "Optimize memory usage using Java 24 features"
/komposteur "Implement virtual threads for parallel video processing"
/komposteur "Debug Java 24 compilation issues in video workflows"
```

### Komposition Processing
Handle complex video timeline and segment processing:

```bash
/komposteur "Process Komposition JSON for YouTube Shorts compilation"
/komposteur "Generate video timeline from audio beat analysis"  
/komposteur "Optimize segment selection for music video creation"
/komposteur "Validate and fix Komposition JSON structure"
```

## Delegation Process

### 1. Intelligent Task Analysis
PULSE master agent automatically:
- Analyzes request for beat-sync, S3, or Java 24 requirements
- Determines if Komposteur expertise is needed
- Prepares delegation with proper context and coordination requirements

### 2. Subagent Processing  
Komposteur subagent:
- Processes request using specialized knowledge
- Coordinates with VideoRenderer subagent if needed
- Applies domain-specific optimizations
- Validates results against quality standards

### 3. Integration Response
Results delivered to PULSE master:
- Processed video segments or Komposition data
- Performance metrics and optimization reports
- Coordination requirements for next pipeline stage
- Quality validation and success metrics

## Response Format

After delegation, PULSE master receives structured response:

```json
{
  "task_id": "komposteur_beat_sync_001",
  "status": "completed|in_progress|failed", 
  "results": {
    "komposition_generated": "path/to/beat_synchronized.json",
    "beat_analysis": {
      "bpm_detected": "135",
      "beat_alignment_accuracy": "99.7%",
      "segment_timing": "microsecond precision maintained"
    },
    "s3_optimizations": {
      "cache_efficiency": "94% hit rate improvement",
      "storage_cost_reduction": "40% through lifecycle policies",
      "parallel_coordination": "5 workers synchronized"
    }
  },
  "coordination": {
    "videorenderer_handoff": "segments ready for crossfade processing",
    "yolo_integration": "timeline prepared for final assembly",
    "resource_requirements": "S3 bucket: skarab, Memory: 2GB peak"
  }
}
```

## Common Usage Patterns

### Music Video Creation Workflow
```bash
# PULSE Master coordinates full workflow
User Request: "Create beat-synchronized music video from these clips"
↓
PULSE Analysis: Requires beat-sync (Komposteur) + crossfades (VideoRenderer)  
↓
/komposteur "Analyze BPM and generate beat-synchronized timeline"
↓
VideoRenderer processes crossfades using Komposteur timeline
↓
PULSE assembles final music video
```

### Performance Optimization Workflow  
```bash
# PULSE Master delegates infrastructure optimization
User Request: "Speed up batch video processing"
↓
PULSE Analysis: S3 caching (Komposteur) + FFmpeg optimization (VideoRenderer)
↓ 
/komposteur "Optimize S3 caching architecture for parallel processing"
↓
VideoRenderer implements FFmpeg performance improvements
↓
PULSE reports combined performance improvements
```

### Java Ecosystem Enhancement
```bash
# PULSE Master requests Java 24 optimizations
User Request: "Improve video processing performance and memory usage"
↓
PULSE Analysis: Java 24 features (Komposteur) + algorithm optimization (VideoRenderer)
↓
/komposteur "Implement Java 24 virtual threads and memory optimizations"
↓ 
VideoRenderer applies algorithm-level performance improvements
↓
PULSE validates combined performance gains
```

## Quality Assurance

### Automatic Validation
Every delegated task includes:
- **Beat Timing Validation**: Microsecond-precision verification for beat-synchronized content
- **S3 Performance Monitoring**: Cache hit rates, storage efficiency, parallel coordination
- **Java 24 Compatibility**: Zero regressions with measurable performance improvements
- **Integration Testing**: Seamless handoff to VideoRenderer and PULSE workflows

### Success Criteria
Tasks must meet these standards:
- **Beat Synchronization**: >99.5% timing accuracy for music video creation
- **S3 Infrastructure**: >90% cache hit rates with optimized storage costs
- **Java 24 Performance**: Measurable improvements in memory usage and processing speed  
- **Integration Quality**: Successful coordination with sister subagent and master workflows

## Coordination with VideoRenderer

### Handoff Patterns
- **Beat-Synchronized Segments**: Komposteur prepares optimally-timed segments for VideoRenderer crossfade processing
- **Quality Standards**: Consistent quality targets across both subagents
- **Resource Coordination**: Efficient resource usage avoiding conflicts
- **Timeline Synchronization**: Precise timing coordination for complex workflows

### Example Coordination
```json
{
  "komposteur_to_videorenderer": {
    "video_segments": ["segment1.mp4", "segment2.mp4"],
    "timing_requirements": "500ms crossfade at beat boundaries", 
    "quality_targets": "maintain microsecond precision",
    "processing_priority": "optimize for batch processing efficiency"
  }
}
```

## Error Handling

### Common Issues and Recovery
- **Beat Detection Failures**: Automatic fallback to manual BPM specification
- **S3 Access Issues**: Graceful degradation to local processing with optimization
- **Java 24 Compatibility**: Version detection and automatic compatibility mode
- **Resource Conflicts**: Intelligent scheduling and resource allocation

### Error Response Format
```json
{
  "error": {
    "type": "beat_detection|s3_access|java24_compatibility|resource_conflict",
    "severity": "critical|high|medium|low",
    "message": "Human-readable error description",
    "recovery_options": ["fallback strategies available"]
  }
}
```

## Best Practices

### Effective Delegation
- **Be Specific**: Include BPM targets, quality requirements, resource constraints
- **Provide Context**: Mention downstream processing needs and integration requirements  
- **Set Priorities**: Indicate if this is time-critical or quality-critical
- **Consider Resources**: Specify S3 access needs, memory constraints, parallel processing requirements

### Optimal Task Descriptions
```bash
# Good: Specific with measurable targets
/komposteur "Create beat-synchronized timeline for 128 BPM track with 16-beat segments and crossfade preparation"

# Good: Clear infrastructure requirements  
/komposteur "Set up S3 multi-worker caching for processing 50+ video files with 90% hit rate target"

# Less ideal: Vague requirements
/komposteur "Make videos sync better"
```

Use this delegation command to leverage Komposteur's specialized expertise in beat synchronization, cloud infrastructure, and Java ecosystem optimization within the PULSE video processing pipeline.
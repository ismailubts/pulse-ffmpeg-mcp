---
name: vdvil
description: Delegate DJ-mixing, audio composition, and audio infrastructure tasks to the VDVIL subagent
---

# VDVIL Delegation Command

Delegates specialized VDVIL tasks to the DJ-mixing infrastructure and audio composition expert subagent. Used by PULSE-FFMPEG-MCP master agent for tasks requiring audio rendering, composition processing, or DJ-mixing capabilities.

## Command Syntax

```bash
/vdvil "<task_description>"
```

## Task Categories

### DJ-Mixing and Audio Composition
Create professional DJ mixes and audio compositions:

```bash
/vdvil "Create DJ mix from 5 audio tracks with smooth crossfading"
/vdvil "Process audio composition from JSON definition for music video"
/vdvil "Generate real-time audio mixing with beat matching"
/vdvil "Mix multiple audio sources with professional DJ transitions"
```

### Audio Infrastructure and Optimization
Optimize audio processing infrastructure and performance:

```bash
/vdvil "Optimize audio rendering performance for multi-track mixing"
/vdvil "Implement new audio format support in VDVIL infrastructure"
/vdvil "Debug audio processing pipeline performance issues"
/vdvil "Enhance binding layer for better component coordination"
```

### Composition Processing and Validation
Handle audio composition formats and validation:

```bash
/vdvil "Convert XML composition to modern JSON format"
/vdvil "Validate audio composition structure and timing accuracy"
/vdvil "Process composition upload and generate audio timeline"
/vdvil "Fix audio composition metadata and track coordination"
```

### Audio-Video Integration Support
Coordinate audio processing with video workflows:

```bash
/vdvil "Prepare audio tracks for video synchronization"
/vdvil "Generate audio timing data for beat-synchronized videos"
/vdvil "Process audio for integration with video crossfades"
/vdvil "Create audio background for music video composition"
```

## Delegation Process

### 1. Audio Task Analysis
PULSE master agent automatically:
- Identifies DJ-mixing, composition, or audio infrastructure requirements
- Analyzes audio quality and performance needs
- Determines VDVIL subagent expertise requirements
- Prepares delegation with audio specifications and coordination needs

### 2. Specialized Audio Processing
VDVIL subagent:
- Applies DJ-mixing expertise and audio composition knowledge
- Processes audio using VDVIL infrastructure and rendering engine
- Implements audio optimization and quality enhancement
- Coordinates with sister subagents for integrated workflows

### 3. High-Quality Audio Results
Delivers to PULSE master:
- Professional-quality mixed audio with optimal transitions
- Validated composition data and audio timeline information
- Performance-optimized audio processing with quality metrics
- Integration-ready outputs for video processing workflows

## Response Format

After delegation, PULSE master receives structured response:

```json
{
  "task_id": "vdvil_mix_001",
  "status": "completed|in_progress|failed",
  "results": {
    "audio_output": ["mixed_audio.wav", "composition_timeline.json"],
    "dj_mixing": {
      "tracks_processed": "5 audio tracks with smooth crossfading",
      "transition_quality": "professional DJ-style transitions applied",
      "timing_accuracy": "microsecond precision maintained"
    },
    "composition_processing": {
      "format_validation": "JSON composition structure validated",
      "timeline_generated": "audio timeline with beat markers",
      "metadata_extracted": "track information and timing data"
    },
    "audio_infrastructure": {
      "rendering_performance": "+30% faster audio processing",
      "memory_optimization": "efficient multi-track handling implemented",
      "format_support": "enhanced compatibility with video workflows"
    }
  },
  "quality_metrics": {
    "audio_fidelity": "high-quality output with minimal loss",
    "processing_speed": "real-time capable for live mixing",
    "memory_efficiency": "optimized for large audio files"
  }
}
```

## Common Usage Patterns

### Music Video Audio Creation
```bash
# PULSE Master coordinates audio creation for music videos
User Request: "Create background audio mix for music video"
↓
PULSE Analysis: Audio mixing (VDVIL) + beat-sync (Komposteur) + video sync (VideoRenderer)
↓
/vdvil "Create professional DJ mix with crossfading for music video background"
↓
Komposteur processes beat synchronization using VDVIL output
↓
VideoRenderer synchronizes video with beat-synchronized audio
↓
PULSE assembles final music video with professional audio
```

### Audio Infrastructure Enhancement
```bash
# PULSE Master delegates audio infrastructure optimization
User Request: "Improve audio processing performance for video workflows"
↓
PULSE Analysis: Audio infrastructure (VDVIL) + video performance (VideoRenderer)
↓
/vdvil "Optimize audio rendering pipeline and binding layer performance"
↓
VideoRenderer benefits from improved audio processing capabilities
↓
PULSE reports unified performance improvements across audio-video pipeline
```

### Composition Processing Workflow
```bash
# PULSE Master handles composition processing and integration
User Request: "Process uploaded audio composition for video project"
↓
PULSE Analysis: Composition processing (VDVIL) + timeline integration (Komposteur)
↓
/vdvil "Validate and process audio composition, generate timeline data"
↓
Komposteur uses composition timeline for beat-synchronized video creation
↓
PULSE coordinates final video assembly with processed audio
```

## Quality Assurance

### Audio Excellence Standards
Every delegated task maintains:
- **Audio Fidelity**: High-quality audio rendering with minimal quality loss
- **Professional Mixing**: DJ-quality crossfading and transition effects
- **Timing Precision**: Microsecond-level accuracy for audio synchronization
- **Format Compatibility**: Seamless integration with video processing workflows

### Performance Standards
- **Real-time Capability**: Audio processing suitable for live mixing applications
- **Memory Efficiency**: Optimized handling of large audio files and multi-track projects
- **Processing Speed**: 25%+ improvement in audio rendering performance
- **Integration Success**: >95% successful coordination with video workflows

## Coordination with Sister Subagents

### Komposteur Collaboration
- **Beat Synchronization**: Provide audio timing data for beat-synchronized video creation
- **Composition Integration**: Share audio composition data for video timeline generation
- **Quality Coordination**: Ensure audio quality standards align with video processing
- **S3 Integration**: Coordinate audio file storage and caching strategies

### VideoRenderer Collaboration
- **Audio-Video Sync**: Provide precisely timed audio for video synchronization
- **Format Optimization**: Ensure audio formats work optimally with video processing
- **Quality Standards**: Maintain consistent audio quality throughout video pipeline
- **Performance Coordination**: Share resource utilization for optimal processing

### Example Multi-Subagent Coordination
```json
{
  "workflow": "professional_music_video_creation",
  "coordination": {
    "vdvil_output": {
      "mixed_audio": "professional_5track_mix.wav",
      "timing_data": "beat_markers_and_transitions.json",
      "quality_specs": "48kHz, 16-bit stereo for video compatibility"
    },
    "komposteur_processing": {
      "input": "timing_data from VDVIL",
      "output": "beat_synchronized_video_timeline.json",
      "coordination": "preserve audio timing precision"
    },
    "videorenderer_integration": {
      "audio_input": "mixed_audio from VDVIL", 
      "video_timeline": "beat_synchronized_timeline from Komposteur",
      "output": "synchronized_music_video.mp4"
    }
  }
}
```

## Error Handling and Recovery

### Common Issues and Solutions
- **Audio Format Incompatibility**: Automatic format conversion with quality preservation
- **Composition Validation Errors**: Detailed error reporting with correction suggestions
- **Performance Bottlenecks**: Intelligent resource allocation and optimization
- **Integration Failures**: Graceful fallback with alternative processing approaches

### Error Response Format
```json
{
  "error": {
    "type": "audio_format|composition_validation|performance_bottleneck|integration_failure",
    "severity": "critical|high|medium|low",
    "message": "Detailed error description with context",
    "recovery_actions": ["attempted recovery strategies"],
    "fallback_options": ["alternative processing approaches"],
    "coordination_impact": "effect on Komposteur and VideoRenderer workflows"
  }
}
```

## Best Practices

### Effective Delegation
- **Specify Audio Requirements**: Include quality targets, format preferences, timing constraints
- **Provide Context**: Mention integration needs with video processing workflows
- **Set Performance Expectations**: Indicate real-time vs batch processing requirements
- **Consider Coordination**: Specify sister subagent dependencies and handoff requirements

### Optimal Task Descriptions
```bash
# Good: Specific with quality and performance targets
/vdvil "Create 5-track DJ mix with professional crossfading, 48kHz quality for video sync"

# Good: Clear composition processing requirements
/vdvil "Validate XML composition structure and convert to JSON with timeline generation"

# Less ideal: Vague requirements
/vdvil "Make audio better"
```

## Integration Benefits

### For Music Video Creation
- **Professional Audio**: DJ-quality mixing and transitions for music videos
- **Perfect Synchronization**: Precise timing coordination with video processing
- **Format Optimization**: Audio prepared specifically for video integration
- **Quality Assurance**: Consistent audio quality throughout video pipeline

### For Audio Infrastructure
- **Performance Optimization**: Enhanced audio processing capabilities
- **Format Support**: Comprehensive audio format compatibility
- **Memory Efficiency**: Optimized resource utilization for large projects
- **Scalability**: Support for complex multi-track compositions and real-time mixing

Use this delegation command to leverage VDVIL's specialized expertise in DJ-mixing, audio composition, and audio infrastructure within the PULSE video processing ecosystem.
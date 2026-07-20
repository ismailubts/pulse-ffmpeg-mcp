# PULSE Master Agent Integration Guide

## Quick Start

This guide shows how to set up and use the PULSE-FFMPEG-MCP hierarchical agent system with Komposteur and VideoRenderer subagents.

## Architecture Overview

```
PULSE-FFMPEG-MCP (Master Agent)
├── Komposteur Subagent (Beat-sync & Java ecosystem)
├── VideoRenderer Subagent (FFmpeg & Performance)
└── Intelligent Task Delegation System
```

## Setup Instructions

### 1. Verify Directory Structure
```
pulse-ffmpeg-mcp/
├── .claude/
│   ├── subagents/
│   │   ├── komposteur/
│   │   │   └── komposteur-subagent.md
│   │   └── videorenderer/
│   │       └── videorenderer-subagent.md
│   └── commands/
│       ├── komposteur-delegate.md
│       └── videorenderer-delegate.md
├── docs/
│   ├── YOLO_MASTER_AGENT_ARCHITECTURE.md
│   └── INTEGRATION_GUIDE.md (this file)
└── CLAUDE.md (updated with agent system)
```

### 2. Configure Workspaces
The subagents operate in relative workspaces:
- **Komposteur**: `../../../komposteur` (from PULSE directory)
- **VideoRenderer**: `../../../VideoRenderer` (from PULSE directory)

### 3. Delegation Commands
PULSE Claude can now use:
- `/komposteur "<task>"` - Beat-sync, S3, Java 24 tasks
- `/videorenderer "<task>"` - FFmpeg, crossfade, performance tasks

## Usage Examples

### Music Video Creation
```
User Request: "Create a 2-minute beat-synchronized music video with smooth crossfades"

PULSE Master Process:
1. Analyzes: Beat-sync needed (Komposteur) + Crossfades needed (VideoRenderer)
2. Delegates to Komposteur: "Generate beat-synchronized timeline for 128 BPM"
3. Delegates to VideoRenderer: "Process segments with optimized crossfades"
4. Coordinates results and assembles final video
5. Validates quality and delivers to user
```

### Performance Optimization
```
User Request: "Video processing is too slow, optimize performance"

PULSE Master Process:
1. Analyzes: S3 caching (Komposteur) + FFmpeg optimization (VideoRenderer)
2. Delegates to Komposteur: "Optimize S3 caching for parallel processing"
3. Delegates to VideoRenderer: "Optimize FFmpeg commands and memory usage"
4. Monitors combined performance improvements
5. Reports unified optimization results
```

### Complex Workflow Management
```
User Request: "Process 50 YouTube videos into beat-synchronized shorts"

PULSE Master Process:
1. Analyzes: Batch processing + beat-sync + format optimization
2. Delegates to Komposteur: "Set up S3 caching and YouTube download workflow"
3. Delegates to VideoRenderer: "Optimize batch format conversion pipeline"
4. Coordinates parallel processing across both subagents
5. Manages progress tracking and error recovery
6. Delivers organized output with quality validation
```

## Communication Patterns

### Sequential Processing
```
PULSE → Komposteur (beat analysis) → VideoRenderer (crossfade) → PULSE (assembly)
```

### Parallel Processing
```
PULSE → {Komposteur: S3 setup, VideoRenderer: format conversion} → PULSE (coordination)
```

### Sister Subagent Collaboration
```
Komposteur → VideoRenderer (beat-synchronized segments for crossfade processing)
VideoRenderer → PULSE (processed segments ready for final assembly)
```

## Quality Standards

### Master Agent Oversight
- **Result Validation**: PULSE verifies all subagent outputs meet quality standards
- **Error Recovery**: Automatic retry mechanisms and fallback strategies
- **Performance Monitoring**: Track subagent response times and success rates
- **User Experience**: Seamless experience regardless of underlying complexity

### Subagent Coordination
- **Quality Consistency**: Uniform standards across all processing stages
- **Resource Efficiency**: Optimal resource utilization and conflict avoidance
- **Timing Precision**: Microsecond-level accuracy maintained across handoffs
- **Format Compatibility**: Seamless data flow between processing stages

## Advanced Features

### Intelligent Task Analysis
PULSE automatically determines:
- Which subagents are needed for each request
- Optimal processing order and coordination
- Resource requirements and constraints
- Quality targets and success criteria

### Error Handling and Recovery
- **Automatic Fallback**: If one subagent fails, PULSE tries alternative approaches
- **Resource Management**: Intelligent resource allocation prevents conflicts
- **Quality Monitoring**: Continuous quality validation with automatic correction
- **User Communication**: Clear status updates and error explanations

### Performance Optimization
- **Parallel Execution**: Both subagents work simultaneously when possible
- **Resource Sharing**: Efficient coordination of memory, CPU, and storage
- **Cache Optimization**: Intelligent caching strategies across all components
- **Batch Processing**: Optimized workflows for processing multiple videos

## Integration Benefits

### For Users
- **Simplified Interface**: Single PULSE interface for all video processing needs
- **Expert Results**: Specialized knowledge from domain expert subagents
- **Better Performance**: Optimized processing through intelligent coordination
- **Quality Assurance**: Master oversight ensures consistent high-quality outputs

### For Development
- **Separation of Concerns**: Each subagent focuses on their core expertise
- **Scalable Architecture**: Easy to add new specialist subagents
- **Maintainable Code**: Clear boundaries and well-defined interfaces
- **Quality Control**: Centralized oversight with distributed expertise

## Monitoring and Metrics

### Success Metrics
- **Task Routing Accuracy**: >95% correct subagent selection
- **Processing Speed**: 30%+ improvement through intelligent delegation  
- **Error Rate**: <5% failed delegations with automatic recovery
- **User Satisfaction**: Simplified workflows with expert-quality results

### Performance Tracking
- **Subagent Response Times**: Monitor individual subagent performance
- **Resource Utilization**: Track memory, CPU, and storage efficiency
- **Quality Metrics**: Measure output quality across all processing stages
- **Integration Success**: Monitor successful handoffs and coordination

## Troubleshooting

### Common Issues
1. **Subagent Not Found**: Verify workspace paths are correct relative to PULSE directory
2. **Communication Failures**: Check subagent definitions and command configurations
3. **Quality Issues**: Verify coordination between subagents and master oversight
4. **Performance Problems**: Monitor resource conflicts and optimization opportunities

### Debugging Steps
1. Check PULSE master agent logs for delegation decisions
2. Verify subagent workspace accessibility and permissions
3. Validate communication protocols and message formats
4. Test individual subagent functionality in isolation
5. Monitor resource usage and coordination patterns

This hierarchical system transforms PULSE-FFMPEG-MCP into a comprehensive video processing orchestrator while maintaining simplicity and reliability for end users.
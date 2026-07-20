# Containerized FFmpeg Architecture Design

## Overview
Transform PULSE-FFMPEG-MCP to use Docker containers for FFmpeg execution while keeping the main application lightweight and dependency-free.

## Current vs Proposed Architecture

### Current (Problematic)
```
Main App Environment
├── Python 3.13
├── FFmpeg binary
├── OpenCV (heavy compilation)
├── Audio libraries
├── Video codecs
└── MCP Server code
```

### Proposed (Clean Separation)
```
Host Environment (Clean)          Docker Container (Isolated)
├── Python 3.13                  ├── Alpine Linux
├── MCP Server code               ├── FFmpeg + codecs
├── Docker client                 ├── Audio libraries  
└── File management               └── Temporary workspace
    ↓                                ↑
    Volume Mounts                    Processed Files
    Input Files ─────────────────────── Output Files
```

## Design Principles

1. **Clean Host Environment**: No FFmpeg dependencies on main system
2. **Portable Execution**: FFmpeg runs in standardized container 
3. **File-based Interface**: Input/output via volume mounts
4. **Security Isolation**: FFmpeg processes contained and sandboxed
5. **Build Speed**: Host builds fast, FFmpeg container pre-built

## Component Design

### 1. FFmpeg Runner Container
```dockerfile
FROM alpine:latest
RUN apk add --no-cache ffmpeg ffprobe
WORKDIR /workspace
ENTRYPOINT ["ffmpeg"]
```

### 2. Containerized FFmpeg Wrapper
```python
class ContainerizedFFmpeg:
    def execute_command(self, cmd: List[str], input_files: List[Path], output_dir: Path):
        # Mount input directory as /input (read-only)
        # Mount output directory as /output (read-write)
        # Execute FFmpeg with path translation
        # Return results with proper file tracking
```

### 3. Path Translation Layer
- Translate host paths to container paths
- Handle relative vs absolute path scenarios
- Ensure security boundaries (no access outside designated dirs)

### 4. File Management System
```
Host Directories:
├── /tmp/music/source/     → Container: /input/
├── /tmp/music/temp/       → Container: /output/
├── /tmp/music/metadata/   → Container: /metadata/
└── /tmp/mcp-traces/       → Container: /traces/
```

## Implementation Strategy

### Phase 1: Basic Container Runner
- Create minimal FFmpeg container
- Implement basic command execution with volume mounts
- Replace simple FFmpeg calls in existing code

### Phase 2: Advanced Features
- Add audio processing capabilities
- Implement complex video operations
- Add performance monitoring and optimization

### Phase 3: Production Hardening
- Security sandboxing and resource limits
- Error handling and recovery
- Performance benchmarking vs current approach

## Benefits

### Build Performance
- **Host builds**: 30 seconds (no FFmpeg compilation)
- **Container builds**: Pre-built, cached on registry
- **CI/CD speed**: 5x faster pipeline execution

### Environment Cleanliness
- **Development**: No multimedia dependencies polluting dev environment
- **Production**: Cleaner deployment with fewer system dependencies
- **Testing**: Isolated FFmpeg testing without affecting host

### Security & Reliability
- **Sandboxing**: FFmpeg execution isolated from main process
- **Resource limits**: Container CPU/memory limits prevent runaway processes
- **Process cleanup**: Automatic cleanup when container exits

### Operational Benefits
- **Debugging**: Container logs separate from application logs
- **Monitoring**: Resource usage tracking per FFmpeg operation
- **Scaling**: Easy horizontal scaling of FFmpeg operations

## Technical Specifications

### Container Requirements
- **Base image**: Alpine Linux (~5MB base)
- **FFmpeg version**: Latest stable with common codecs
- **Resource limits**: 2GB RAM, 2 CPU cores max per operation
- **Execution timeout**: 10 minutes max per operation
- **Storage**: Ephemeral, no persistent data in container

### Security Model
- **User context**: Non-root user (ffmpeg:ffmpeg)
- **Network**: No network access (--network none)
- **Filesystem**: Read-only except for designated output directories
- **Capabilities**: Minimal Linux capabilities, no privileged access

### Performance Expectations
- **Startup overhead**: ~100ms per container creation
- **Execution**: Equivalent to native FFmpeg performance
- **Cleanup**: Automatic container removal after completion
- **Concurrency**: Support for multiple parallel FFmpeg operations

## Migration Plan

### Phase 1: Drop-in Replacement
1. Create `ContainerizedFFmpegWrapper` class
2. Implement same interface as current `FFMPEGWrapper`
3. Add feature flag to switch between implementations
4. Test with existing operations

### Phase 2: Optimization
1. Add container pooling for frequently used operations
2. Implement smart volume mounting based on command analysis
3. Add performance monitoring and comparison metrics
4. Optimize for common use cases

### Phase 3: Full Migration
1. Remove native FFmpeg dependency from main application
2. Update documentation and deployment guides
3. Add container management features (health checks, restart policies)
4. Implement advanced features like GPU acceleration support

## Testing Strategy

### Unit Tests
- Container creation and cleanup
- Path translation accuracy
- Command execution verification
- Error handling scenarios

### Integration Tests  
- End-to-end video processing workflows
- Performance comparison with native implementation
- Resource usage validation
- Concurrent operation testing

### Performance Benchmarks
- Build time comparison (current vs containerized)
- Runtime performance (overhead measurement)
- Resource usage analysis
- Scalability testing

## Implementation Files

### New Components
- `src/containerized_ffmpeg.py` - Main wrapper class
- `src/docker_manager.py` - Container lifecycle management
- `src/path_translator.py` - Host/container path translation
- `docker/ffmpeg-runner/Dockerfile` - FFmpeg container definition
- `tests/test_containerized_ffmpeg.py` - Test suite

### Modified Components
- `src/ffmpeg_wrapper.py` - Add containerized backend option
- `src/server.py` - Configuration for container vs native execution
- `pyproject.toml` - Remove heavy FFmpeg dependencies
- `Dockerfile` - Simplified main application container

## Rollout Strategy

### Development Environment
1. Feature flag: `USE_CONTAINERIZED_FFMPEG=true`
2. Fallback to native implementation if Docker unavailable
3. Side-by-side testing and validation

### CI/CD Pipeline
1. Build both native and containerized versions
2. Run parallel test suites
3. Performance comparison reporting
4. Gradual migration of test scenarios

### Production Deployment
1. Blue-green deployment with rollback capability
2. A/B testing for performance validation
3. Monitoring and alerting for container health
4. Documentation and operational runbooks

This architecture provides a clean separation of concerns while maintaining the full functionality of the current system with significant improvements in build speed, environment cleanliness, and operational reliability.
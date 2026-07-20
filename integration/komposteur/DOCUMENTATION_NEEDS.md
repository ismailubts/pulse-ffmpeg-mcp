# Komposteur Library Documentation Needs

## 🎯 Current Consumer Perspective

As a consumer trying to integrate Komposteur library into the FFMPEG MCP server, here's what would make me more efficient:

## 📚 Missing Documentation Categories

### 1. **API Reference Documentation**
**What I need:**
- Complete JavaDoc for all public methods
- Method signatures with parameter types
- Return type specifications
- Exception handling documentation

**Current gap:** 
- No clear entry point for Python integration
- Unknown method names for kompost.json processing
- Unclear parameter formats and validation rules

**Example of what I'd want:**
```java
/**
 * Process a kompost.json file with curated FFMPEG workflows
 * @param kompostFilePath Absolute path to kompost.json file
 * @param outputDir Directory for generated video files
 * @return ProcessingResult with output paths and metadata
 * @throws InvalidKompostException if JSON format is invalid
 * @throws FFmpegException if video processing fails
 */
public ProcessingResult processKompostFile(String kompostFilePath, String outputDir)
```

### 2. **Integration Patterns Documentation**
**What I need:**
- How to properly initialize the library from external code
- Lifecycle management (startup, shutdown, resource cleanup)
- Thread safety considerations
- Memory management best practices

**Current gap:**
- No clear initialization pattern for py4j integration
- Unknown if library is thread-safe
- No guidance on resource cleanup

**Example of what I'd want:**
```markdown
## Python Integration via Py4J

### Setup
1. Start gateway: `java -cp komposteur-core.jar py4j.GatewayServer`
2. Connect: `gateway = JavaGateway()`
3. Initialize: `komposteur = gateway.entry_point.createKomposteur()`

### Cleanup
Always call `komposteur.shutdown()` and `gateway.shutdown()`
```

### 3. **Kompost JSON Schema Documentation**
**What I need:**
- Complete JSON schema with all supported fields
- Field validation rules and constraints
- Examples of different workflow types
- Version compatibility information

**Current gap:**
- No formal schema definition
- Unknown which fields are required vs optional
- No examples of complex workflows
- Unclear version evolution strategy

**Example of what I'd want:**
```json
{
  "$schema": "https://schemas.komposteur.io/v1.0/kompost-schema.json",
  "title": "Kompost Configuration",
  "type": "object",
  "required": ["version", "sources", "segments"],
  "properties": {
    "version": {
      "type": "string",
      "enum": ["1.0", "1.1"],
      "description": "Schema version for compatibility"
    }
  }
}
```

### 4. **FFMPEG Integration Documentation**
**What I need:**
- How Komposteur translates JSON to FFMPEG commands
- List of curated FFMPEG filters and their parameters
- Performance characteristics of different operations
- Quality vs speed trade-offs

**Current gap:**
- No visibility into FFMPEG command generation
- Unknown optimization strategies
- No performance benchmarks
- Unclear quality settings impact

**Example of what I'd want:**
```markdown
## Curated FFMPEG Filters

### film_noir_grade
- **FFMPEG Command**: `curves=vintage,colorbalance=rs=0.2:gs=-0.1:bs=-0.2`
- **Performance**: ~2.3x realtime on typical hardware
- **Quality Impact**: Preserves detail while creating film aesthetic
- **Parameters**: contrast (0.5-2.0), saturation (0.0-1.0), vignette (0.0-1.0)
```

### 5. **Error Handling and Debugging**
**What I need:**
- Comprehensive error code documentation
- Debugging techniques and common issues
- Logging configuration options
- Performance monitoring capabilities

**Current gap:**
- Unknown error types and recovery strategies
- No debugging guidance
- Unclear logging configuration

**Example of what I'd want:**
```markdown
## Error Handling

### KomposteurException Types
- `InvalidSchemaException`: JSON doesn't match expected schema
- `SourceNotFoundException`: Referenced media file not found  
- `FFmpegProcessingException`: Video processing failed
- `TimingValidationException`: Beat timing calculations invalid

### Debugging
Enable debug logging: `KomposteurConfig.setLogLevel(DEBUG)`
Common issues: [link to troubleshooting guide]
```

## 🛠️ Immediate Needs for MCP Integration

### Priority 1: Entry Point Clarity
```java
// What I need to exist:
public class KomposteurEntryPoint {
    public static KomposteurEntryPoint create() { ... }
    public ProcessingResult processKompost(String jsonPath) { ... }
    public void shutdown() { ... }
}
```

### Priority 2: Kompost JSON Examples
- Film noir workflow example
- Beat synchronization example  
- Multi-segment composition example
- Error handling examples

### Priority 3: Python Bridge Documentation
- Complete py4j integration guide
- Alternative integration methods (JNI, subprocess)
- Performance comparison of integration approaches

## 📋 Documentation Format Preferences

### 1. **Living Documentation**
- README with quick start examples
- Separate detailed guides for complex topics
- Code examples that actually run
- Version-specific documentation

### 2. **Interactive Examples**
- Working sample projects
- Command-line tools for testing
- Docker containers with pre-configured environment

### 3. **API Discoverability**
- IDE-friendly JavaDoc
- REST API documentation style (even for Java)
- Searchable method index
- Cross-references between related methods

## 🎯 Success Metrics

**I would consider the documentation successful if:**

1. **5-Minute Quick Start**: I can process a kompost.json file within 5 minutes of first seeing the library
2. **Clear Error Messages**: When something fails, I immediately know what to fix
3. **Pattern Recognition**: I can identify which curated FFMPEG patterns to use for my use case
4. **Integration Confidence**: I understand the production implications of different configuration choices

## 🔧 Current Blockers for MCP Integration

1. **No clear entry point** - Cannot determine how to instantiate Komposteur from external code
2. **No kompost.json processing method** - Main workflow unclear
3. **No Python integration guide** - py4j setup failing
4. **No error handling patterns** - Don't know how to handle failures gracefully

**Bottom line**: I need a "Hello World" example that shows kompost.json → processed video in 10 lines of code, with clear error handling.
# Komposteur Filter Implementation Proposal

## 🎯 **FOR: Komposteur Claude**

This proposal outlines how to implement filter support in Komposteur using it as a library, specifically for translating kompost.json filter commands to MCP video processing operations.

**Reference**: See `KOMPOSTEUR_MCP_INTEGRATION_COMPLETE_SPECIFICATION.md` for complete architecture context.

## 🔧 **FILTER TRANSLATION REQUIREMENTS**

### **Current Integration Point**
- **Working**: Komposteur discovers `/src/komposition_processor.py` 
- **Working**: JSON data flows to MCP processor
- **Missing**: Filter command interpretation and application

### **JSON Filter Structure (MCP Expected)**
```json
{
  "segments": [
    {
      "sourceRef": "video.mp4",
      "operation": "trim",
      "params": {...},
      "filters": [
        {"type": "blur", "params": {"radius": 2}},
        {"type": "custom", "ffmpeg_filter": "-vf 'eq=brightness=0.1'"}
      ]
    }
  ],
  "global_filters": [
    {"type": "fade", "params": {"fade_in": 1.0, "fade_out": 2.0}}
  ]
}
```

## 📋 **IMPLEMENTATION TASKS**

### **1. Filter Command Parser**
**Location**: Komposteur codebase  
**Task**: Parse natural language filter descriptions to structured filter commands

```java
// Example implementation needed in Komposteur:
public class FilterTranslator {
    public List<FilterSpec> translateFilters(String description) {
        // "add blur effect" -> {"type": "blur", "params": {"radius": 1.5}}
        // "make it darker" -> {"type": "custom", "ffmpeg_filter": "-vf 'eq=brightness=0.05'"}
    }
}
```

### **2. Kompost JSON Enhancement**
**Task**: Extend kompost.json generation to include filter specifications

**Required Additions**:
- Segment-level `filters` array
- Global `global_filters` array  
- Filter parameter validation

### **3. MCP Interface Compliance**
**Task**: Ensure generated JSON matches MCP processor expectations

**Critical**: MCP processor expects these exact field names:
- `filters` (array on segments)
- `global_filters` (array on root)
- Filter types: `"blur"`, `"custom"`, `"fade"`

## 🎨 **FILTER TYPE MAPPING**

### **Supported Filter Types (MCP Ready)**
```java
// These work in current MCP system:
filterMap.put("blur", (radius) -> new Filter("blur", Map.of("radius", radius)));
filterMap.put("brightness", (value) -> new Filter("custom", 
    Map.of("ffmpeg_filter", "-vf 'eq=brightness=" + value + "'")));
filterMap.put("contrast", (value) -> new Filter("custom", 
    Map.of("ffmpeg_filter", "-vf 'eq=contrast=" + value + "'")));
filterMap.put("saturation", (value) -> new Filter("custom", 
    Map.of("ffmpeg_filter", "-vf 'eq=saturation=" + value + "'")));
```

### **Filter Parameter Ranges**
- **Blur radius**: 0.1 - 5.0 (higher = more blur)
- **Brightness**: -1.0 to 1.0 (0 = normal, negative = darker)
- **Contrast**: 0.1 - 3.0 (1.0 = normal, higher = more contrast)
- **Saturation**: 0.0 - 3.0 (1.0 = normal, 0 = grayscale)

## 🔄 **PROCESSING PIPELINE INTEGRATION**

### **Current MCP Processing Order**
1. Source video registration
2. Basic operations (trim, resize)
3. **→ Segment filters applied here** ←
4. Video concatenation
5. Audio processing
6. **→ Global filters applied here** ←
7. Final output

### **Filter Application Timing**
- **Segment filters**: Applied to individual clips before concatenation
- **Global filters**: Applied to final concatenated video

## 📝 **SPECIFIC IMPLEMENTATION GUIDANCE**

### **1. Natural Language → Filter Mapping** 
```java
// Examples of what Komposteur should generate:
"make it blurry" → {"type": "blur", "params": {"radius": 1.5}}
"darker mood" → {"type": "custom", "ffmpeg_filter": "-vf 'eq=brightness=0.05:contrast=1.2'"}
"dreamy effect" → {"type": "blur", "params": {"radius": 0.8}}
"vibrant colors" → {"type": "custom", "ffmpeg_filter": "-vf 'eq=saturation=1.3'"}
```

### **2. JSON Generation Pattern**
```java
// Add to segment generation:
if (hasFilterRequests(description)) {
    List<Filter> filters = translateFilters(description);
    segment.put("filters", filters);
}

// Add to root level:
if (hasGlobalEffects(composition)) {
    List<Filter> globalFilters = translateGlobalFilters(composition);
    kompost.put("global_filters", globalFilters);
}
```

### **3. Error Handling**
- Invalid filter parameters → Use safe defaults
- Unknown filter types → Skip with warning log
- Missing MCP processor → Graceful degradation without filters

## 🧪 **TESTING STRATEGY**

### **Test Cases Needed**
1. **Single filter**: Blur on one segment
2. **Multiple filters**: Blur + brightness on same segment  
3. **Global filters**: Fade in/out on entire video
4. **Complex combination**: Segment filters + global filters
5. **Error cases**: Invalid parameters, missing fields

### **Validation**
- Generated JSON validates against MCP schema
- Filter parameters within acceptable ranges
- FFmpeg filter syntax correctness

## 🎯 **SUCCESS CRITERIA**

**When implementation is complete, this should work:**

1. **Natural language input**: "Create a dreamy video with blur effects"
2. **Komposteur generates**: Kompost JSON with appropriate filter specs
3. **MCP processes**: Applies filters during video generation
4. **Output**: Video file with visual effects applied

## 🔗 **COLLABORATION POINTS**

### **MCP Side (Already Working)**
- ✅ Filter parsing from JSON
- ✅ FFmpeg filter application
- ✅ Segment and global filter processing
- ✅ Error handling and fallbacks

### **Komposteur Side (Needed)**
- ❓ Natural language → filter mapping
- ❓ JSON generation with filter specs
- ❓ Parameter validation and defaults
- ❓ Integration with existing composition logic

## 📊 **IMPLEMENTATION PRIORITY**

1. **High**: Basic blur and brightness filters
2. **Medium**: Contrast and saturation filters  
3. **Low**: Advanced custom FFmpeg filters
4. **Future**: Complex multi-stage filter chains

**Reference the complete specification document for full architecture context and collaborative development approach.**
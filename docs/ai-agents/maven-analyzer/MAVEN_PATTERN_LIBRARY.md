# Maven Plugin Pattern Library - Specialized Knowledge Base

## Overview

Comprehensive pattern library for **instant Maven failure diagnosis**. Each pattern includes exact error signatures, root cause analysis, and specific fix instructions.

## Core Maven Plugins Deep Dive

### **maven-compiler-plugin** 🔧

#### Pattern 1: Java Version Mismatches
```json
{
  "error_signatures": [
    "release version (\\d+) not supported",
    "invalid target release: (\\d+)",
    "Source option (\\d+) is no longer supported"
  ],
  "root_cause": "Compilation target version doesn't match available JDK",
  "detection_logic": "Extract version numbers from error + check pom.xml vs environment",
  "solutions": [
    {
      "fix": "Update pom.xml compiler target",
      "example": "<maven.compiler.target>17</maven.compiler.target>",
      "confidence": 0.95
    },
    {
      "fix": "Update GitHub Actions setup-java version", 
      "example": "java-version: '17'",
      "confidence": 0.90
    }
  ],
  "common_variations": [
    "Java 8 → 11 migration issues",
    "Java 17 → 21 upgrade problems", 
    "CI environment vs local JDK differences"
  ]
}
```

#### Pattern 2: Module System Configuration
```json
{
  "error_signatures": [
    "package module.lang does not exist",
    "invalid flag: --add-modules",
    "module not found: java.base"
  ],
  "root_cause": "Module system (Java 9+) configuration on incompatible Java version",
  "detection_logic": "Module-related errors + Java version < 9",
  "solutions": [
    {
      "fix": "Remove module-info.java for Java 8 compatibility",
      "confidence": 0.85
    },
    {
      "fix": "Upgrade to Java 9+ to use module system",
      "confidence": 0.90
    },
    {
      "fix": "Remove --add-modules compiler arguments",
      "confidence": 0.80
    }
  ]
}
```

#### Pattern 3: Missing Dependencies
```json
{
  "error_signatures": [
    "cannot access class file for (\\w+\\.\\w+) is missing",
    "package (\\w+\\.\\w+) does not exist",
    "cannot find symbol.*class (\\w+)"
  ],
  "root_cause": "Required dependency not in compile classpath",
  "detection_logic": "Extract missing class/package name + search in pom.xml",
  "solutions": [
    {
      "fix": "Add missing dependency to pom.xml",
      "confidence": 0.90,
      "research_hint": "Search Maven Central for class name"
    },
    {
      "fix": "Check dependency scope (compile vs provided)",
      "confidence": 0.85
    }
  ]
}
```

### **maven-surefire-plugin** 🧪

#### Pattern 1: Test Discovery Issues
```json
{
  "error_signatures": [
    "No tests were executed",
    "Test run finished after \\d+ ms.*\\[ *0 containers found"
  ],
  "root_cause": "Tests not discovered due to naming or location issues",
  "detection_logic": "Zero tests executed + check file structure",
  "solutions": [
    {
      "fix": "Rename test files to end with Test.java",
      "example": "UserServiceTest.java (not UserServiceTests.java)",
      "confidence": 0.90
    },
    {
      "fix": "Move tests to src/test/java directory",
      "confidence": 0.85
    },
    {
      "fix": "Check JUnit 5 vs JUnit 4 configuration",
      "confidence": 0.80
    }
  ],
  "common_causes": [
    "Test files named *Tests.java instead of *Test.java",
    "Tests in wrong directory (src/main/java)",
    "Missing JUnit dependencies",
    "JUnit 4 vs 5 annotation conflicts"
  ]
}
```

#### Pattern 2: Test Execution Failures
```json
{
  "error_signatures": [
    "Tests run: (\\d+), Failures: (\\d+), Errors: (\\d+)",
    "Test (\\w+\\.\\w+)\\.(\\w+) failed"
  ],
  "root_cause": "Specific test methods failing",
  "detection_logic": "Extract test class and method names from failure output",
  "solutions": [
    {
      "fix": "Run specific failing test: mvn test -Dtest=ClassName#methodName",
      "confidence": 0.95
    },
    {
      "fix": "Check test assertions and expected vs actual values",
      "confidence": 0.85
    }
  ],
  "extraction_patterns": [
    "Failed tests:\\s+(\\w+\\.\\w+\\.\\w+)",
    "at (\\w+\\.\\w+)\\.(\\w+)\\((\\w+\\.java):(\\d+)\\)"
  ]
}
```

#### Pattern 3: Memory and Performance Issues
```json
{
  "error_signatures": [
    "java.lang.OutOfMemoryError",
    "Test execution timed out",
    "Unable to create new native thread"
  ],
  "root_cause": "JVM resource limits exceeded during test execution",
  "solutions": [
    {
      "fix": "Increase JVM memory in surefire configuration",
      "example": "<argLine>-Xmx2048m</argLine>",
      "confidence": 0.90
    },
    {
      "fix": "Reduce parallel test execution",
      "example": "<parallel>false</parallel>",
      "confidence": 0.80
    }
  ]
}
```

### **maven-dependency-plugin** 📦

#### Pattern 1: GitHub Packages Authentication
```json
{
  "error_signatures": [
    "Could not transfer artifact.*from/to github.*401",
    "Could not transfer artifact.*from/to github.*403",
    "repository element was not specified in the POM"
  ],
  "root_cause": "GitHub Packages authentication or configuration issues",
  "detection_logic": "GitHub repository URL + 401/403 status codes",
  "solutions": [
    {
      "fix": "Add GITHUB_TOKEN to environment or settings.xml",
      "confidence": 0.95,
      "example": "export GITHUB_TOKEN=ghp_..."
    },
    {
      "fix": "Add GitHub Packages repository to pom.xml",
      "confidence": 0.90,
      "example": "<repository><id>github</id><url>https://maven.pkg.github.com/...</url></repository>"
    },
    {
      "fix": "Check token permissions include packages:read",
      "confidence": 0.85
    }
  ]
}
```

#### Pattern 2: SNAPSHOT Dependencies
```json
{
  "error_signatures": [
    "Could not resolve dependencies.*SNAPSHOT",
    "Could not find artifact.*SNAPSHOT"
  ],
  "root_cause": "SNAPSHOT dependency not available in repositories",
  "solutions": [
    {
      "fix": "Check if external project published latest SNAPSHOT",
      "confidence": 0.85
    },
    {
      "fix": "Use specific version instead of SNAPSHOT",
      "confidence": 0.80
    },
    {
      "fix": "Add snapshot repository if missing",
      "confidence": 0.75
    }
  ]
}
```

#### Pattern 3: Version Conflicts
```json
{
  "error_signatures": [
    "Dependency convergence error",
    "Found duplicate and different classes",
    "NoClassDefFoundError.*Expected (\\w+) but was (\\w+)"
  ],
  "root_cause": "Multiple versions of same dependency causing conflicts",
  "solutions": [
    {
      "fix": "Use dependencyManagement to force specific versions",
      "confidence": 0.90
    },
    {
      "fix": "Add exclusions to remove conflicting transitive dependencies",
      "confidence": 0.85
    },
    {
      "fix": "Run 'mvn dependency:tree' to analyze conflict",
      "confidence": 0.95
    }
  ]
}
```

### **exec-maven-plugin** ⚡

#### Pattern 1: Main Class Issues
```json
{
  "error_signatures": [
    "Could not find or load main class (\\w+\\.\\w+)",
    "Error: Main method not found in class (\\w+\\.\\w+)"
  ],
  "root_cause": "Main class not in classpath or incorrect configuration",
  "solutions": [
    {
      "fix": "Verify main class exists and has public static void main method",
      "confidence": 0.90
    },
    {
      "fix": "Check mainClass configuration in exec plugin",
      "confidence": 0.85
    },
    {
      "fix": "Ensure class is in target/classes after compilation",
      "confidence": 0.80
    }
  ]
}
```

## Pattern Matching Algorithm

### **Error Signature Extraction**
```python
def extract_error_signature(maven_log: str) -> ErrorSignature:
    """Extract key identifying features from Maven build log"""
    
    # Step 1: Find build failure section
    failure_section = extract_section_after("[ERROR] BUILD FAILURE")
    
    # Step 2: Identify failing plugin
    plugin_pattern = r"Failed to execute goal ([\w\.-]+):([\w\.-]+):([\w\.-]+):([\w\.-]+)"
    plugin_match = re.search(plugin_pattern, failure_section)
    
    # Step 3: Extract error message
    error_patterns = [
        r"compilation failed: (.+)",
        r"Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+ (.+)",
        r"Could not resolve dependencies (.+)",
        r"Could not transfer artifact (.+)"
    ]
    
    # Step 4: Create signature for pattern matching
    return ErrorSignature(
        plugin=plugin_match.group() if plugin_match else "unknown",
        error_text=extracted_error,
        context_lines=get_surrounding_context(failure_section, 5)
    )
```

### **Pattern Confidence Scoring**
```python
def calculate_confidence(pattern: Pattern, error_sig: ErrorSignature) -> float:
    """Calculate confidence score for pattern match"""
    
    base_confidence = pattern.base_confidence
    
    # Exact error text match
    if exact_match(pattern.signature, error_sig.error_text):
        base_confidence += 0.1
    
    # Plugin context match
    if pattern.plugin == error_sig.plugin:
        base_confidence += 0.05
        
    # Historical success rate
    if pattern.success_rate > 0.9:
        base_confidence += 0.05
    
    # Multiple pattern variations matched
    if count_matched_variations(pattern, error_sig) > 1:
        base_confidence += 0.05
        
    return min(base_confidence, 1.0)
```

## Cross-Project Learning

### **Pattern Evolution**
```json
{
  "pattern_id": "java_version_mismatch_001", 
  "original_signature": "release version 21 not supported",
  "evolved_signatures": [
    "release version 21 not supported",
    "invalid target release: 21", 
    "Source option 21 is no longer supported"
  ],
  "projects_seen": ["project-a", "project-b", "komposteur"],
  "success_rate": 0.94,
  "last_updated": "2024-01-15",
  "confidence_evolution": [0.80, 0.85, 0.90, 0.94]
}
```

### **Project-Specific Adaptations**
- **Komposteur**: S3 dependency authentication patterns
- **VDVIL**: Audio processing library configuration patterns  
- **MCP Projects**: Python-Maven interop patterns
- **Enterprise**: Organization-specific repository and security patterns

This pattern library transforms the **build-detective** (new name!) into a **Maven specialist** that gets smarter with every project it analyzes.
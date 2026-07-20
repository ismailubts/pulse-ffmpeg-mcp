# Build Detective Maven Build Log Parsing Guide

## Maven Multi-Module Build Structure

### Build Reactor Order
```
[INFO] Reactor Summary for video-renderer-base 1.3.3-SNAPSHOT:
[INFO] 
[INFO] video-renderer-base ................................ SUCCESS [  0.123 s]
[INFO] image-core ......................................... SUCCESS [  1.456 s]
[INFO] video-renderer-core ................................ SUCCESS [  2.234 s]
[INFO] ffmpeg ............................................. SUCCESS [  0.987 s]
[INFO] video-renderer ..................................... SUCCESS [  3.456 s]
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
[INFO] Total time:  8.256 s
[INFO] Finished at: 2025-08-21T21:45:30+02:00
[INFO] ------------------------------------------------------------------------
```

### Module-Specific Patterns
Each module shows:
```
[INFO] --- Building image-core 1.3.3-SNAPSHOT ---
[INFO] --- maven-compiler-plugin:3.11.0:compile (default-compile) @ image-core ---
[INFO] Changes detected - recompiling the module!
[INFO] Compiling 12 source files to /path/to/target/classes
```

### Key Parsing Patterns for BD

#### 1. **Reactor Summary Parsing**
```regex
Reactor Summary for (.+):
[\s\S]*?
BUILD (SUCCESS|FAILURE)
[\s\S]*?
Total time:\s+([0-9.]+)\s*s
```

#### 2. **Individual Module Results**
```regex
\[INFO\]\s+(.+?)\s+\.+\s+(SUCCESS|FAILURE)\s+\[\s*([0-9.]+)\s*s\s*\]
```

#### 3. **Compilation Per Module**
```regex
\[INFO\]\s+Compiling (\d+) source files to (.+)
```

#### 4. **Test Execution Per Module**
```regex
\[INFO\]\s+Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+), Time elapsed: ([0-9.]+) s - in (.+)
```

## Maven Build Phases and Goals

### Phase Progression
```
validate → compile → test → package → verify → install → deploy
```

### Common Build Log Patterns

#### **Dependency Resolution**
```
[INFO] --- maven-dependency-plugin:3.2.0:resolve-sources (default) @ module-name ---
[INFO] The following files have been resolved:
[INFO]    no.lau.vdvil:image-core:jar:sources:1.3.3-SNAPSHOT:compile
```

#### **Compilation Phase**
```
[INFO] --- maven-compiler-plugin:3.11.0:compile (default-compile) @ module-name ---
[INFO] Changes detected - recompiling the module!
[INFO] Compiling 23 source files to /Users/user/project/module/target/classes
[INFO] /Users/user/project/src/main/java/SomeClass.java:[45,12] warning: [deprecation] method() is deprecated
```

#### **Test Phase**
```
[INFO] --- maven-surefire-plugin:3.5.3:test (default-test) @ module-name ---
[INFO] -------------------------------------------------------
[INFO]  T E S T S
[INFO] -------------------------------------------------------
[INFO] Running no.lau.vdvil.TestSuite
[INFO] Tests run: 5, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 0.123 s - in TestSuite
```

#### **Package Phase**
```
[INFO] --- maven-jar-plugin:3.2.2:jar (default-jar) @ module-name ---
[INFO] Building jar: /Users/user/project/module/target/module-1.3.3-SNAPSHOT.jar
[INFO] --- maven-install-plugin:2.5.2:install (default-install) @ module-name ---
[INFO] Installing /path/to/jar to ~/.m2/repository/no/lau/vdvil/module/1.3.3-SNAPSHOT/
```

## Error Patterns in Multi-Module Builds

### **Module Build Failure**
```
[INFO] video-renderer-base ................................ SUCCESS [  0.123 s]
[INFO] image-core ......................................... SUCCESS [  1.456 s]
[INFO] video-renderer-core ................................ FAILURE [  0.234 s]
[INFO] ffmpeg ............................................. SKIPPED
[INFO] video-renderer ..................................... SKIPPED
```

### **Dependency Conflict**
```
[WARNING] The POM for no.lau.vdvil:missing-artifact:jar:1.0.0 is missing, no dependency information available
[ERROR] Failed to execute goal on project video-renderer-core: Could not resolve dependencies
```

### **Compilation Errors**
```
[ERROR] COMPILATION ERROR : 
[INFO] -------------------------------------------------------------
[ERROR] /path/to/source/Class.java:[23,8] error: cannot find symbol
[ERROR]   symbol:   class MissingClass
[ERROR]   location: class ExistingClass
```

### **Test Failures**
```
[ERROR] Tests run: 10, Failures: 2, Errors: 0, Skipped: 0, Time elapsed: 2.345 s <<< FAILURE! - in TestClass
[ERROR] testMethod(TestClass)  Time elapsed: 0.123 s  <<< FAILURE!
[ERROR] Expected: <true>
[ERROR]      but: was <false>
```

## Enhanced BD Parsing Implementation

### **Multi-Module Aware Parser**
```python
def parse_reactor_summary(self, stdout: str) -> Dict[str, Any]:
    """Parse Maven reactor summary for multi-module builds"""
    reactor_info = {
        "total_modules": 0,
        "successful_modules": 0,
        "failed_modules": 0,
        "skipped_modules": 0,
        "module_results": [],
        "total_build_time": 0,
        "reactor_order": []
    }
    
    # Parse reactor summary section
    summary_pattern = r"Reactor Summary for (.+?):\s*\n([\s\S]*?)BUILD (SUCCESS|FAILURE)"
    summary_match = re.search(summary_pattern, stdout)
    
    if summary_match:
        project_name = summary_match.group(1)
        summary_content = summary_match.group(2)
        build_result = summary_match.group(3)
        
        # Parse individual module results
        module_pattern = r"\[INFO\]\s+(.+?)\s+\.+\s+(SUCCESS|FAILURE|SKIPPED)\s+\[\s*([0-9.]+)\s*s\s*\]"
        modules = re.findall(module_pattern, summary_content)
        
        for module_name, status, duration in modules:
            module_info = {
                "name": module_name.strip(),
                "status": status,
                "duration_seconds": float(duration)
            }
            reactor_info["module_results"].append(module_info)
            reactor_info["total_modules"] += 1
            
            if status == "SUCCESS":
                reactor_info["successful_modules"] += 1
            elif status == "FAILURE":
                reactor_info["failed_modules"] += 1
            elif status == "SKIPPED":
                reactor_info["skipped_modules"] += 1
    
    # Parse total time
    total_time_pattern = r"Total time:\s+([0-9.]+)\s*s"
    time_match = re.search(total_time_pattern, stdout)
    if time_match:
        reactor_info["total_build_time"] = float(time_match.group(1))
    
    return reactor_info

def parse_module_specific_info(self, stdout: str) -> Dict[str, Any]:
    """Parse module-specific build information"""
    modules = {}
    
    # Find module build sections
    module_sections = re.findall(r"--- Building (.+?) ---", stdout)
    
    for module in module_sections:
        module_info = {
            "compilation": {"source_files": 0, "target_dir": ""},
            "tests": {"run": 0, "failures": 0, "errors": 0, "skipped": 0},
            "artifacts": [],
            "warnings": [],
            "errors": []
        }
        
        # Find compilation info for this module
        compile_pattern = rf"Building {re.escape(module)}[\s\S]*?Compiling (\d+) source files to (.+)"
        compile_match = re.search(compile_pattern, stdout)
        if compile_match:
            module_info["compilation"]["source_files"] = int(compile_match.group(1))
            module_info["compilation"]["target_dir"] = compile_match.group(2)
        
        # Find test results for this module
        test_pattern = rf"Tests run: (\d+), Failures: (\d+), Errors: (\d+), Skipped: (\d+).*?in (.+)"
        for test_match in re.finditer(test_pattern, stdout):
            if module in test_match.group(5):  # Check if this test belongs to current module
                module_info["tests"]["run"] += int(test_match.group(1))
                module_info["tests"]["failures"] += int(test_match.group(2))
                module_info["tests"]["errors"] += int(test_match.group(3))
                module_info["tests"]["skipped"] += int(test_match.group(4))
        
        # Find artifacts created for this module
        jar_pattern = rf"Building jar: (.+{re.escape(module)}.+\.jar)"
        for jar_match in re.finditer(jar_pattern, stdout):
            module_info["artifacts"].append(jar_match.group(1))
        
        modules[module] = module_info
    
    return modules

def extract_dependency_issues(self, stdout: str, stderr: str) -> List[Dict[str, Any]]:
    """Extract dependency resolution issues"""
    issues = []
    
    # Missing dependencies
    missing_deps = re.findall(r"Could not find artifact (.+?) in (.+)", stdout + stderr)
    for artifact, repo in missing_deps:
        issues.append({
            "type": "missing_dependency",
            "artifact": artifact,
            "repository": repo,
            "severity": "error"
        })
    
    # Version conflicts
    conflict_pattern = r"Dependency convergence error for (.+?) paths to dependency are:\s*([\s\S]*?)(?=\[|$)"
    conflicts = re.findall(conflict_pattern, stdout + stderr)
    for artifact, paths in conflicts:
        issues.append({
            "type": "version_conflict",
            "artifact": artifact,
            "paths": paths.strip(),
            "severity": "warning"
        })
    
    return issues
```

## Maven Profile and Property Handling

### **Profile Activation Patterns**
```
[INFO] --- The following profiles are active: ex-integration,development
[INFO] --- maven-help-plugin:3.2.0:active-profiles (default-cli) @ project ---
```

### **Property Resolution**
```
[INFO] --- Properties resolved: project.version=1.3.3-SNAPSHOT, maven.compiler.target=21
```

## Build Lifecycle Hook Detection

### **Pre/Post Build Goals**
```
[INFO] --- maven-clean-plugin:3.2.0:clean (default-clean) @ module ---
[INFO] --- maven-resources-plugin:3.3.0:resources (default-resources) @ module ---
[INFO] --- maven-compiler-plugin:3.11.0:compile (default-compile) @ module ---
[INFO] --- maven-resources-plugin:3.3.0:testResources (default-testResources) @ module ---
[INFO] --- maven-compiler-plugin:3.11.0:testCompile (default-testCompile) @ module ---
[INFO] --- maven-surefire-plugin:3.5.3:test (default-test) @ module ---
[INFO] --- maven-jar-plugin:3.2.2:jar (default-jar) @ module ---
[INFO] --- maven-install-plugin:2.5.2:install (default-install) @ module ---
```

## BD Integration Points

### **Key Parsing Enhancements Needed**
1. **Multi-module build order and dependencies**
2. **Module-specific test results aggregation**
3. **Cross-module dependency resolution tracking**
4. **Profile-aware build analysis**
5. **Incremental build detection (changed modules only)**

This guide provides BD with the patterns and structure needed to properly parse complex Maven multi-module builds and extract meaningful information for build analysis and comparison.
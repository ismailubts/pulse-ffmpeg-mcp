# Incremental Fix Workflow

**Based on PR 22 Resolution Learnings**

## 🎯 Problem-Solving Methodology

### **Layer-by-Layer Approach**
Don't attempt to fix all issues simultaneously. Instead, solve one layer at a time:

1. **Layer 1: File/Path Issues** 
   - Missing files, incorrect paths, gitignored dependencies
   - Example: `temp/` directory files not available in CI

2. **Layer 2: Module/Import Issues**
   - Python import errors, missing dependencies
   - Example: `ModuleNotFoundError: No module named 'src'`

3. **Layer 3: Configuration Issues**
   - Docker, CI workflow, environment mismatches
   - Example: Complex workflows with missing dependencies

4. **Layer 4: Integration Issues**
   - Merge conflicts, version mismatches, architectural changes
   - Example: Main branch conflicts after extended feature work

## 🔧 Implementation Protocol

### **Before Any CI Changes**
```bash
# 1. Run BD Local CI validation
python3 scripts/bd_local_ci.py

# 2. If Docker changes, test locally
python3 scripts/bd_local_ci.py --docker

# 3. Check specific components
docker build -f Dockerfile.ci -t test . && docker run --rm test
```

### **Fix Implementation Cycle**
```bash
# Fix ONE issue at a time
1. Identify the single root cause
2. Implement minimal fix
3. Test locally with BD
4. Commit with specific description
5. Push and verify CI
6. Move to next issue ONLY after success
```

### **When to Stop and Reassess**
- ❌ **STOP** if 3+ issues emerge from single change
- ❌ **STOP** if "simple fix" touches 5+ files  
- ❌ **STOP** if local BD tests fail after change
- ✅ **CONTINUE** if each fix resolves exactly one issue

## 📋 Issue Classification

### **🟢 Simple Fixes (Proceed)**
- Single file path corrections
- Missing dependency additions
- Obvious import statement fixes
- Clear documentation updates

### **🟡 Moderate Fixes (Caution)**  
- Docker configuration changes
- Workflow modifications
- Multi-file import restructuring
- Environment variable changes

### **🔴 Complex Fixes (Stop & Plan)**
- Architectural changes
- Multi-component integration  
- Major dependency upgrades
- Merge conflict resolution

## 🚨 Failure Recovery

### **If Layer N Fails**
1. **Revert Layer N changes**: `git reset --hard HEAD~1`
2. **Reassess approach**: Is this the right layer?
3. **Break down further**: Can Layer N be split into N1, N2?
4. **Document learning**: Add to knowledge base

### **Escalation Criteria**
- Same issue reoccurs after 3 different approaches
- Fix affects >10 files or >3 subsystems
- Local tests pass but CI consistently fails
- Merge conflicts become recursive

## ✅ Success Indicators

### **Per Layer**
- BD local CI passes after change
- Docker builds succeed locally  
- Specific error message disappears
- No new issues introduced

### **Overall Success**
- All GitHub Actions green
- PR shows "Ready to merge"
- No conflicts with main branch
- BD confidence score >8/10

## 📚 Documentation Requirements

### **For Each Fix**
```markdown
## Layer N: [Issue Type]
- **Problem**: Specific error message or failure
- **Root Cause**: Why this happened  
- **Solution**: Exact change made
- **Verification**: How success was confirmed
- **Side Effects**: Any new issues or changes
```

### **For Complex Workflows**
- Create TODO_RESTORE_[COMPONENT].md before disabling
- Document original value and restoration plan
- Include step-by-step recovery instructions
- Set deletion criteria (restore or permanent removal)

## 🔄 Continuous Improvement

### **After Each PR**
1. **Assess methodology**: Did layer approach work?
2. **Update patterns**: What new issue types emerged?
3. **Enhance BD tools**: What validation was missing?
4. **Document lessons**: Update workflow based on learnings

### **Success Metrics**
- **Time to resolution**: Incremental should be faster
- **Issue containment**: Fixes shouldn't create new problems  
- **CI failure reduction**: Local validation should catch issues
- **Knowledge transfer**: Future similar issues easier to solve

## 🎯 Application Example: PR 22

**Layer 1**: Fixed missing temp/ files → Dockerfile.ci path corrections  
**Layer 2**: Fixed module imports → Added src/ directory to Docker  
**Layer 3**: Fixed workflow complexity → Replaced with simple CI test  
**Layer 4**: Fixed merge conflicts → Systematic resolution strategy  

Each layer built on the previous, avoiding compound complexity and enabling focused problem-solving.

---

**Key Learning**: One issue, one fix, one test, one commit. Compound changes create compound problems.
---
name: document-generator
description: Generate and update documentation from git changes and chat history. Extract architectural knowledge, setup procedures, and best practices into AI-agent-optimized docs. Automatically detect and fix stale information. Use when onboarding, refactoring, or updating project state.
user-invocable: true
disable-model-invocation: false
---

# Document Generator Skill

Generate and maintain Thea documentation from code changes and chat history.

## When to Use This Skill

- After major features or refactoring to update architecture docs
- When onboarding new developers (extract from chat history)
- Quarterly documentation audits to fix stale information
- Before deployment to ensure docs reflect current state
- When setup procedures change (dependencies, environment, configuration)

## Documentation Architecture

```
docs/
├── setup.md                    # Installation & environment setup
├── architecture.md             # (Generated) Component design & data flow
├── best-practices.md          # (Generated) Code patterns & standards
├── troubleshooting.md         # (Generated) Common issues & solutions
├── dependency-matrix.md       # (Generated) Version compatibility
├── gpu-acceleration.md        # (Generated) GPU/CUDA setup
├── api-reference.md           # (Generated) Module/function reference
├── configuration.md           # (Generated) Config file reference
├── CHANGELOG.md               # (Generated) Version history with git tags
└── video_creator.md           # Existing workflow guide
```

## Document Generation Workflow

### Phase 1: Git Diff Analysis
```powershell
# Extract all commits since last doc update
git log --since="2 weeks ago" --name-only --oneline
git diff HEAD~20..HEAD --stat

# Find modified files that affect documentation
git diff HEAD~20..HEAD -- *.py setup.py requirements.txt
```

**Parse Output**:
- New dependencies → Update `dependency-matrix.md`
- GPU code changes → Update `gpu-acceleration.md`
- Config file changes → Update `configuration.md`
- API changes → Update `api-reference.md`
- Bug fixes → Update `troubleshooting.md`

### Phase 2: Chat History Extraction
**Source**: Copilot chat transcripts + user explanations

**Extract**:
```
Pattern: "How to [do X]?" 
→ Extract solution → `troubleshooting.md` or `setup.md`

Pattern: "What is [architecture Y]?"
→ Extract explanation → `architecture.md`

Pattern: "Best practice for [Z]?"
→ Extract pattern → `best-practices.md`

Pattern: "[Component] does [functionality]"
→ Extract responsibility → `api-reference.md`
```

### Phase 3: Consistency Checking
```python
# Check for inconsistencies between docs and code
1. Version numbers in docs vs requirements.txt
2. Command examples that are no longer valid
3. Configuration keys that don't exist
4. File paths that have moved
5. Outdated API documentation
```

### Phase 4: Document Generation
Generate structured documents optimized for AI consumption.

## Document Format Specifications

### Format 1: AI-Parseable Structured Markdown

**Use for**: Architecture, API reference, configuration

```markdown
# [Document Title]

**Last Updated**: 2026-06-13  
**Scope**: [Brief description]  
**Audience**: Developers / CI/CD / Setup

## Quick Reference
| Item | Value | Status |
|------|-------|--------|
| Required Python | 3.10+ | ✓ Current |
| GPU Support | CUDA 12.x | ✓ Tested |

## Concept 1
**Definition**: Concise description in one sentence.  
**When Used**: Specific use case  
**Key Points**:
- Point 1
- Point 2

## Code Example
\`\`\`python
# Executable code with comments
# Lines: 5-12 of src/motion_assessment/analyzer.py

import torch
from motion_assessment import MotionAnalyzer

analyzer = MotionAnalyzer(gpu=True)
results = analyzer.analyze(frames)
\`\`\`

## Related
- [Link to architecture.md]
- [Link to api-reference.md]
```

### Format 2: Setup Instructions (Executable)

**Use for**: Setup, installation, configuration

```markdown
# Setup: [Component Name]

## Prerequisites
- [ ] Python 3.10+
- [ ] CUDA 12.x (for GPU)
- [ ] 8GB RAM minimum

## Installation

### Step 1: Clone Repository
\`\`\`powershell
# PowerShell (Windows)
git clone https://github.com/user/thea.git
cd thea
\`\`\`

### Step 2: Create Virtual Environment
\`\`\`powershell
# Create venv
python -m venv venv

# Activate (Windows)
.\\venv\\Scripts\\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate
\`\`\`

### Step 3: Install Dependencies
\`\`\`powershell
# Install from requirements.txt
pip install -r requirements.txt

# Verify installation
python -c "import torch; print(torch.cuda.is_available())"
\`\`\`

## Verification
\`\`\`powershell
# Run quick test
pytest tests/fast -v

# Expected Output: 12 passed in 2.34s
\`\`\`

## Troubleshooting
| Error | Cause | Solution |
|-------|-------|----------|
| ModuleNotFoundError | Missing dependency | `pip install [package]` |
| CUDA not available | GPU drivers outdated | Update NVIDIA drivers |

## Next Steps
- [ ] Configure GPU settings (see configuration.md)
- [ ] Run sample pipeline (python main.py)
```

### Format 3: Best Practices

**Use for**: Coding patterns, standards, architectural decisions

```markdown
# Best Practice: [Name]

**Applies to**: [Module/Component]  
**Priority**: HIGH | MEDIUM | LOW  
**Since**: Version 1.0

## Pattern
Concise description of the practice.

## Why This Matters
- Reason 1: Specific benefit
- Reason 2: Risk mitigation
- Reason 3: Maintainability

## Correct Way (✓)
\`\`\`python
# Code example showing best practice
# Location: src/motion_assessment/analyzer.py:45-52

def analyze_motion(frames):
    # Use context manager for resource cleanup
    with torch.cuda.device(0):
        results = process_frames(frames)
    torch.cuda.empty_cache()  # Clean up GPU memory
    return results
\`\`\`

## Incorrect Way (✗)
\`\`\`python
# Code example showing anti-pattern

def analyze_motion(frames):
    results = process_frames(frames)
    # GPU memory leaks if exception occurs
    return results
\`\`\`

## Real-World Impact
**Benefit**: Reduces GPU memory usage by 40%, prevents OOM errors  
**Cost**: Adds 2-3ms per batch  
**Frequency**: Applied to all motion analysis code

## See Also
- [Related pattern: X]
- [Configuration: Y]
```

### Format 4: Troubleshooting Guide

**Use for**: Common issues, debugging strategies

```markdown
# Troubleshooting: [Issue Category]

## Issue 1: [Specific Error Message]

**Symptoms**: What the user sees  
**Root Cause**: Why it happens  
**Probability**: COMMON | RARE  

### Quick Fix (90% Success)
\`\`\`powershell
# Step 1: Check status
python -c "import torch; print(torch.cuda.is_available())"

# Step 2: Clear cache
Remove-Item -Path $env:USERPROFILE\\.cache\\torch -Recurse -Force

# Step 3: Retry
python main.py
\`\`\`

### Deep Troubleshooting (If Quick Fix Fails)
\`\`\`powershell
# Diagnostic script
python -m thea.diagnostics --verbose

# Check logs
Get-Content logs/thea.log -Tail 50
\`\`\`

### Escalation
If still failing, check:
1. [Link to dependency-matrix.md]
2. [Link to architecture.md - GPU section]
3. File GitHub issue with output from diagnostics

## Issue 2: [Another Common Issue]
...
```

### Format 5: API Reference (For AI Agents)

**Use for**: Module/function documentation with machine-readable structure

```markdown
# API Reference: motion_assessment

**Module**: `motion_assessment.analyzer`  
**Status**: STABLE (v1.0+)  
**GPU**: Required (CUDA 12.x)

## Class: MotionAnalyzer
\`\`\`python
class MotionAnalyzer:
    """Analyze optical flow and motion vectors in video frames."""
```

**Constructor**:
```python
def __init__(self, gpu: bool = True, model: str = "raft")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| gpu | bool | True | Use GPU acceleration |
| model | str | "raft" | Optical flow model (raft, farneback) |

**Returns**: MotionAnalyzer instance

**Raises**:
- ValueError: If GPU requested but not available
- ImportError: If model weights not found

**Example**:
```python
analyzer = MotionAnalyzer(gpu=True, model="raft")
```

---

**Method**: `analyze(frames)`

```python
def analyze(self, frames: np.ndarray) -> Dict[str, np.ndarray]
```

**Parameters**:
- `frames`: Shape (N, H, W, 3), dtype uint8, range 0-255

**Returns**:
```python
{
    "motion_vectors": np.ndarray,      # Shape (N-1, H, W, 2)
    "magnitude": np.ndarray,            # Shape (N-1, H, W)
    "categories": np.ndarray,           # Shape (N-1,) - ["static", "slow", "medium", "fast"]
}
```

**Raises**:
- RuntimeError: If GPU memory insufficient
- ValueError: If frames shape invalid

**Performance**: ~50ms per frame (1080p) on RTX 3080

**Example**:
```python
motion = analyzer.analyze(frames)
print(motion["magnitude"].mean())  # Average motion magnitude
```

---

## Related Classes
- VideoReader (read video frames)
- Slicer (segment using motion data)
```

## Code Snippet Standards

### PowerShell Syntax (Windows)
```markdown
\`\`\`powershell
# Comments use # (native PowerShell syntax)

# Variable assignment
$pythonPath = "C:\\Python310\\python.exe"

# Command execution
& $pythonPath -m pytest tests/ -v

# Conditional
if (Test-Path "venv\\Scripts\\Activate.ps1") {
    .\\venv\\Scripts\\Activate.ps1
}

# Loop
Get-ChildItem "*.py" | ForEach-Object {
    Write-Host $_.FullName
}
\`\`\`
```

### Python Syntax
```markdown
\`\`\`python
# Always include import statements
import torch
from motion_assessment import MotionAnalyzer

# Add source location comments for code from actual files
# Location: src/motion_assessment/analyzer.py:45-60

analyzer = MotionAnalyzer(gpu=True)
results = analyzer.analyze(frames)

# Add performance notes for critical code
# Performance: O(n*m) where n=frames, m=pixels
print(f"Motion magnitude: {results['magnitude'].mean():.2f}")
\`\`\`
```

### Bash Syntax (Linux/Mac)
```markdown
\`\`\`bash
# Use bash comments with #

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
\`\`\`
```

## Stale Information Detection & Update

### Automated Checks
```python
# Version check: Are documented versions current?
documented_python = "3.10+"
current_python = sys.version_info
if current_python < (3, 10):
    FLAG_STALE: "Python requirement outdated"

# Command check: Can documented commands execute?
result = subprocess.run(documented_command, capture_output=True)
if result.returncode != 0:
    FLAG_STALE: "Setup command no longer works"

# Dependency check: Are documented versions available?
latest_torch = get_latest_version("torch")
documented_torch = "2.0+"
if latest_torch > documented_torch:
    FLAG_REVIEW: "PyTorch updated to {latest_torch}"

# Path check: Do documented file paths exist?
if not os.path.exists(documented_path):
    FLAG_STALE: "File path no longer valid"
```

### Update Protocol
1. **Mark as Stale**: Add `⚠️ STALE INFORMATION` banner at top
2. **Document Issue**: Add update reason and date
3. **Provide Alternative**: Include working approach
4. **Set Review Date**: When to re-verify

**Example**:
```markdown
⚠️ **STALE INFORMATION - Last verified 2026-05-01**
This section references FFmpeg 4.2, but project now requires 4.4+.
See [updated instructions](configuration.md#ffmpeg) for current setup.

---

## Legacy Setup (FFmpeg 4.2)
...

## Current Setup (FFmpeg 4.4+)
...
```

## Integration with Chat History

### Extract Documentation from Conversations
```
User: "How do I enable GPU acceleration?"
Agent: "Set gpu=True in analyzer..."
→ Extract to troubleshooting.md or setup.md

User: "Why does motion assessment take so long?"
Agent: "It computes optical flow for every frame..."
→ Extract to best-practices.md (performance tuning)

User: "What's the architecture of motion_assessment?"
Agent: "It has three components: optical flow, motion vectors, categorization..."
→ Extract to architecture.md
```

### Documentation Auto-Generation Commands

When user asks to update docs:

```powershell
# Generate all docs from current state
python -m thea.docs generate --all --from-git

# Generate specific doc from git changes
python -m thea.docs generate architecture --since "2 weeks ago"

# Validate all docs against current code
python -m thea.docs validate --fix-stale

# Generate from chat history (experimental)
python -m thea.docs extract-from-chat --output troubleshooting.md
```

## Maintenance Schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Validate docs vs code | Weekly | CI/CD |
| Update from git changes | After major refactoring | Developer |
| Extract from chat history | Monthly | Tech lead |
| Audit for stale info | Quarterly | Tech lead |
| Regenerate API reference | After API changes | Developer |
| Update dependency matrix | When deps change | DevOps |

## Quality Checklist for Generated Docs

- [ ] All code examples are copy-paste executable
- [ ] PowerShell syntax highlighted correctly
- [ ] Python code includes source location comments
- [ ] All file paths use forward slashes or proper escaping
- [ ] Setup instructions include prerequisites
- [ ] Troubleshooting has quick fix + deep dive
- [ ] API reference includes parameter types and returns
- [ ] Stale information clearly marked with date
- [ ] Related documents linked appropriately
- [ ] Last updated timestamp is current
- [ ] All tools/commands tested in past 30 days

---
name: dependency-analyzer
description: Analyze Thea's dependencies for updates, security vulnerabilities, and version conflicts. Use to maintain package health and identify integration risks.
user-invocable: true
disable-model-invocation: false
---

# Dependency Analyzer Skill

Manage and analyze Thea's Python and system dependencies.

## When to Use This Skill

- Audit for security vulnerabilities in requirements
- Plan dependency updates
- Resolve version conflicts
- Identify breaking changes in upstream packages
- Check compatibility across components

## Key Dependencies

### Video/Image Processing
| Package | Purpose | Current | Min Version | Risk |
|---------|---------|---------|-------------|------|
| OpenCV | Frame processing, optical flow | 4.x | 4.5 | Medium (API changes) |
| FFmpeg | Video encoding/decoding | 4.x | 4.2 | Low (stable) |
| Pillow | Image utilities | 9.x | 8.0 | Low |
| scikit-image | Advanced image operations | 0.19 | 0.18 | Low |

### GPU/ML
| Package | Purpose | Current | Min Version | Risk |
|---------|---------|---------|-------------|------|
| PyTorch | GPU tensor operations | 2.x | 1.13 | High (breaking changes frequent) |
| CUDA Toolkit | GPU compute | 12.x | 11.8 | Low (backward compatible) |
| cuDNN | CUDA acceleration | 8.x | 8.0 | Low |

### Core Python
| Package | Purpose | Current | Min Version | Risk |
|---------|---------|---------|-------------|------|
| NumPy | Array operations | 1.24+ | 1.21 | Medium (Python 3.9+ required) |
| SciPy | Scientific computing | 1.9+ | 1.7 | Low |

### Testing
| Package | Purpose | Current | Min Version | Risk |
|---------|---------|---------|-------------|------|
| pytest | Test framework | 7.x | 6.0 | Low (backward compatible) |
| pytest-cov | Coverage reporting | 4.x | 3.0 | Low |

## Vulnerability Checking

### Automated Tools
```bash
# Safety checks against known vulnerabilities
pip install safety
safety check

# Bandit for code security issues
bandit -r . -ll

# pip-audit (Python 3.7+)
pip-audit --desc
```

### Common Vulnerabilities

- OpenCV: Potential DLL hijacking (Windows)
- PyTorch: Model loading from untrusted sources
- FFmpeg: Protocol vulnerabilities (disable remote access)

## Dependency Conflict Resolution

### Version Pinning Strategy
```
requirements.txt:
numpy==1.24.3         # Critical: exact version
opencv==4.8.0         # Important: patch version
torch>=2.0,<3.0       # Flexible: major version range
pytest>=7.0           # Loose: any recent version
```

### Finding Conflicts
```bash
# Check compatibility
pip install --dry-run --no-deps -r requirements.txt

# Show dependency tree
pipdeptree

# Check transitive dependencies
pip show -r opencv-python
```

## Update Planning

### Safe Update Flow
1. **Test in CI first** (not production)
2. **Check changelog** for breaking changes
3. **Update minor versions first** (non-breaking)
4. **Verify tests pass** 
5. **Benchmark performance** (especially for OpenCV, torch)
6. **Deploy to staging** before production

### High-Risk Updates
These require careful testing:
- PyTorch major versions
- OpenCV major versions
- Python version upgrades (3.11 → 3.12)
- CUDA toolkit updates

## Integration Impact Analysis

### Critical Path
1. **Motion Assessment** depends on: PyTorch, OpenCV, CUDA
2. **Slicer** depends on: FFmpeg, NumPy
3. **Downscaler** depends on: OpenCV, Pillow

Breaking changes in #1 impact entire pipeline.

### Compatibility Matrix

```
Python 3.9 → 3.12 compatibility:
✓ NumPy 1.24+
✓ PyTorch 2.0+
✓ OpenCV 4.5+
✗ Older CUDA versions
```

## Maintenance Tasks

### Weekly
- Monitor security advisories
- Check for critical patches

### Monthly
- Audit dependencies with `safety check`
- Review new minor versions
- Run full test suite with latest versions

### Quarterly
- Plan major version updates
- Assess new tool options
- Update documentation

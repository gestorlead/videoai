# 📋 VideoAI Project Inventory Report
**Date:** 2024-06-26  
**Branch:** restructure  
**Purpose:** Complete inventory before project restructuring

## 🗂️ Current Structure Overview

### Root Directory (/root/projetos/videoai-web/)
```
├── .taskmaster/         # TaskMaster project management
├── app/                 # Duplicate/Legacy directory
│   └── core/           
│       └── celery.py   # Single file (295 bytes)
├── monitoring/          # Monitoring configurations
├── scripts/             # Utility scripts
├── videoai/            # MAIN PROJECT DIRECTORY (should be root)
├── .env                # Environment variables (root)
├── .env.example        # Example environment file
└── [other config files]
```

### Main Project Directory (videoai/)
Contains the entire application codebase that should be moved to root:
- app/ - Main FastAPI application code
- src/ - Legacy code structure 
- api/ - API related files
- alembic/ - Database migrations
- tests/ - Test suite
- docs/ - Documentation
- scripts/ - Utility scripts
- Docker configurations
- Multiple documentation files (*.md)

## 🔍 Issues Identified

### 1. **Duplicate Directories**
- /app/core/ (root) - Contains only one file: celery.py
- /videoai/app/ - Actual application code
- /videoai/src/ - Legacy code structure
- /videoai/videoai/ - Nested duplicate directory

### 2. **Multiple .env Files**
- /.env - Root environment file
- /videoai/.env - Project environment file
- /videoai/.env.backup - Backup file

### 3. **VideoAI References**
- **70 occurrences** found across Python, YAML, and documentation files
- Main files affected:
  - auto-sub.yaml - Docker compose configuration
  - README files
  - Various Python imports and references

### 4. **Unnecessary Files/Directories**
- /videoai/venv/ - Virtual environment (should not be in repo)
- Multiple __pycache__ directories
- Log files
- Temporary files

## 📊 Statistics

| Category | Count |
|----------|-------|
| Total .env files | 4 |
| VideoAI references | 70 |
| Duplicate app directories | 3 |
| Files to be moved | ~1000+ |
| Legacy directories | 2 (src/, api/) |

## 🎯 Migration Plan Summary

1. **Move** all contents from /videoai/ to root
2. **Delete** duplicate directories and files
3. **Merge** .env files into single root .env
4. **Replace** all VideoAI references with VideoAI
5. **Clean** unnecessary files (venv, cache, logs)
6. **Update** all imports and paths

## ⚠️ Critical Items

- **Database migrations** in /videoai/alembic/ must be preserved
- **Docker configurations** need path updates after move
- **Import statements** will need comprehensive updates
- **CI/CD workflows** in .github/ need path adjustments

## 📝 Next Steps

1. Create backup of current state
2. Begin systematic directory flattening
3. Update configuration files
4. Search and replace VideoAI → VideoAI
5. Test all functionality after restructuring

---
*This inventory will be used as reference during the restructuring process*

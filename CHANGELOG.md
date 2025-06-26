# Changelog

All notable changes to VideoAI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-12-26

### 🎉 Initial Release - Project Restructuring and Rebranding

This release marks the complete transformation from AutoSub to VideoAI with a comprehensive project restructuring.

### Added
- **Complete Project Restructuring**: Moved from nested `videoai/` directory structure to clean root-level organization
- **New Package Structure**: Professional Python package with proper `__init__.py` and entry points
- **Entry Point**: Added `python -m app` command-line interface with help, host, port, and reload options
- **Development Tooling**: Comprehensive setup with Black, Ruff, MyPy, Pytest configurations in `pyproject.toml`
- **Environment Management**: Consolidated `.env` configuration with all necessary variables
- **Docker Setup**: Updated Docker Compose with proper service names and environment variables
- **Documentation**: Complete README.md rewrite with new architecture, quick start, and contribution guidelines
- **Contributing Guide**: Comprehensive CONTRIBUTING.md with development workflow and standards
- **Git Hygiene**: Updated `.gitignore` with comprehensive rules for Python, Docker, and development files
- **CI/CD Workflows**: GitHub Actions updated for new repository structure and naming

### Changed
- **Complete Rebranding**: All references changed from `AutoSub/autosub` to `VideoAI/videoai`
- **Repository Structure**: Flat, professional directory layout with canonical folders:
  - `app/` - Main application code
  - `docs/` - Documentation with organized reports
  - `scripts/` - Utility scripts
  - `examples/` - Usage examples
  - `alembic/` - Database migrations
  - `.github/` - CI/CD workflows
- **Package Metadata**: Updated all package information, URLs, and descriptions
- **Requirements**: Updated to comprehensive 70+ dependency list with modern versions
- **Configuration Files**: All Docker, environment, and config files updated for new structure

### Removed
- **Legacy Structure**: Eliminated nested `videoai/videoai/` directories and duplicates
- **Obsolete Files**: Removed redundant configuration files, cache directories, and temporary files
- **Old References**: Completely eliminated all AutoSub references and legacy naming
- **Duplicate Code**: Consolidated multiple `.env` files and configuration duplicates

### Fixed
- **Import Structure**: All imports updated to new package structure
- **File Paths**: Docker and configuration files updated with correct relative paths
- **Cache Issues**: Removed all `__pycache__` directories from version control
- **Dependency Resolution**: Updated all package dependencies and references

### Infrastructure
- **Zero AutoSub References**: Complete verification that no legacy references remain
- **Clean Git History**: Proper commit history with meaningful messages and structure
- **Development Environment**: Automated environment setup with `regenerate-venv.sh` script
- **Code Quality**: Pre-configured linting, formatting, and type checking tools

### Migration Notes
- **Breaking Change**: This is a complete restructuring - existing installations need fresh setup
- **New Repository**: Project moved to `https://github.com/gestorlead/videoai`
- **Environment Setup**: Use `./regenerate-venv.sh` for clean environment setup
- **Entry Point**: New command line interface: `python -m app --help`

### Performance
- **Optimized Structure**: Cleaner import paths and reduced complexity
- **Development Speed**: Improved development workflow with automated tooling
- **Build Performance**: Optimized Docker builds with better layer caching

---

## [0.x.x] - Legacy AutoSub Versions

Previous versions under the AutoSub name are archived. This changelog starts fresh with the VideoAI rebrand and restructuring.

---

For more details about any release, see the [GitHub Releases](https://github.com/gestorlead/videoai/releases) page.

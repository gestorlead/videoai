# Contributing to VideoAI

Thank you for your interest in contributing to VideoAI! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- Git
- Basic understanding of FastAPI and async Python

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/videoai.git
   cd videoai
   ```

2. **Set Up Environment**
   ```bash
   ./regenerate-venv.sh
   source venv/bin/activate
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys for testing
   ```

4. **Start Development Services**
   ```bash
   docker-compose up -d postgres redis rabbitmq
   ```

5. **Run the Application**
   ```bash
   python -m app --reload
   ```

## 🛠️ Development Workflow

### Code Quality Standards

We maintain high code quality using automated tools:

```bash
# Format code (required before commits)
black .

# Lint code (must pass)
ruff .

# Type checking (must pass)
mypy app/

# Run tests (must pass)
pytest
```

### Pre-commit Hooks

Install pre-commit hooks to automatically check code quality:

```bash
pre-commit install
```

### Branch Naming

Use descriptive branch names:
- `feature/add-video-processing`
- `fix/image-generation-timeout`
- `docs/update-api-documentation`
- `refactor/optimize-celery-tasks`

### Commit Messages

Follow conventional commit format:

```
feat: add new video processing provider
fix: resolve timeout issues in image generation
docs: update API documentation for v1.1
refactor: optimize Celery task performance
test: add integration tests for social media publishing
```

## 📝 Code Guidelines

### Python Style
- Follow PEP 8 (enforced by Black)
- Use type hints for all functions
- Write docstrings for public functions/classes
- Keep functions focused and small

### API Design
- Follow RESTful principles
- Use proper HTTP status codes
- Include comprehensive error handling
- Document all endpoints with FastAPI/OpenAPI

### Example Function
```python
async def generate_image(
    prompt: str,
    provider: str = "openai",
    size: str = "1024x1024"
) -> ImageGenerationResult:
    """
    Generate an image using the specified AI provider.
    
    Args:
        prompt: The text prompt for image generation
        provider: AI provider to use (openai, piapi, etc.)
        size: Output image dimensions
        
    Returns:
        ImageGenerationResult with URL and metadata
        
    Raises:
        ProviderError: If the AI provider fails
        ValidationError: If parameters are invalid
    """
    # Implementation here
```

## 🧪 Testing

### Test Structure
```
tests/
├── unit/           # Unit tests for individual functions
├── integration/    # Integration tests for API endpoints
├── fixtures/       # Test data and fixtures
└── conftest.py     # Pytest configuration
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/unit/test_image_generation.py

# Run tests with specific marker
pytest -m "not slow"
```

### Writing Tests
```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_generate_image_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/images/generate",
            json={"prompt": "test image", "provider": "openai"}
        )
        assert response.status_code == 200
        assert "job_id" in response.json()
```

## 📖 Documentation

### API Documentation
- All endpoints must be documented with FastAPI/OpenAPI
- Include request/response examples
- Document error responses and status codes

### Code Documentation
- Write clear docstrings for all public functions
- Include type hints for all parameters and return values
- Document complex algorithms and business logic

### README Updates
- Update README.md for new features
- Include usage examples for new functionality
- Update installation instructions if needed

## 🐛 Issue Reporting

### Bug Reports
Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version, etc.)
- Error logs and stack traces

### Feature Requests
Include:
- Clear description of the proposed feature
- Use cases and benefits
- Potential implementation approach
- Examples of similar features in other projects

## 🔄 Pull Request Process

### Before Submitting
1. Ensure all tests pass
2. Run code quality checks (black, ruff, mypy)
3. Update documentation if needed
4. Add tests for new functionality
5. Update CHANGELOG.md if applicable

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass
```

### Review Process
1. Automated checks must pass (CI/CD)
2. Code review by maintainers
3. Testing in development environment
4. Approval and merge

## 🏗️ Architecture Guidelines

### Adding New Providers
When adding new AI providers:

1. Create provider class inheriting from `BaseProvider`
2. Implement required methods (`generate`, `validate_config`, etc.)
3. Add provider configuration to settings
4. Write comprehensive tests
5. Update documentation

### Celery Tasks
For new async tasks:

1. Create task in appropriate module (`app/tasks/`)
2. Use proper error handling and retries
3. Include progress tracking for long-running tasks
4. Add monitoring and logging
5. Write integration tests

### Database Changes
For schema changes:

1. Create Alembic migration
2. Test migration up/down
3. Update model classes
4. Add/update serializers
5. Update API endpoints if needed

## 🚀 Release Process

### Version Numbering
We follow Semantic Versioning:
- `MAJOR.MINOR.PATCH`
- Major: Breaking changes
- Minor: New features (backward compatible)
- Patch: Bug fixes (backward compatible)

### Changelog
Update CHANGELOG.md with:
- New features
- Bug fixes
- Breaking changes
- Migration notes

## 💬 Community

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Discord**: Real-time chat (link in README)

### Code of Conduct
We follow the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

## 📚 Resources

### Learning Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Python Async Programming](https://docs.python.org/3/library/asyncio.html)

### Project Resources
- [Architecture Documentation](docs/architecture.md)
- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)

---

Thank you for contributing to VideoAI! 🎬✨

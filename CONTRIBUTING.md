# Contributing to Tender Compliance System

Thank you for your interest in contributing to the Tender Compliance System.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/tender-compliance.git
cd tender-compliance

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest ruff
```

## Running the Application

```bash
cd backend
python app/main.py
```

The API server starts at `http://localhost:8012`. API docs at `http://localhost:8012/docs`.

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=backend
```

## Code Quality

We use `ruff` for linting:

```bash
ruff check .
ruff check --fix .
```

## Project Structure

- `backend/app/services/` - Core business logic (parser, rule engine, scorer, analyzer)
- `backend/app/api/` - FastAPI route definitions
- `backend/app/models/` - Pydantic data models
- `backend/app/rules/` - Rule configuration files
- `tests/` - Test suite

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes and add tests
4. Ensure all tests pass (`pytest tests/ -v`)
5. Run linting (`ruff check .`)
6. Commit with a clear message
7. Push and open a Pull Request

## Commit Message Convention

Use the format: `type(scope): description`

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests
- `refactor`: Code refactoring

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Python version and OS

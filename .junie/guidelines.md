# You are an Astro and Vue js expert
# You are a python, langChain and AI expert

# Code Generation Rules
- Do not analyze *.BAK or .bak files
- ALWAYS use vue best practices for frontend code
- ALWAYS follow Python code quality standards and linting rules

## General Guidelines

- Keep changes minimal
- Focus on task requirements only
- Ensure all generated code passes configured linting tools

## File Modification Rules

- Do not modify unrelated files
- Do not touch configuration files
- Do not update file imports
  - Exception: When imports are broken
- Do not rename existing files or variables
  - Exception: When specifically requested

## Code Refactoring Rules

- Do not refactor existing code
  - Exception: When specifically requested

## Python Code Quality Rules

### Formatting (Black)
- Use line length of 120 characters (as configured)
- Target Python 3.9.6 syntax
- Let black handle all formatting automatically

### Import Organization (isort)
- Group imports: standard library, third-party, first-party (backend, tests)
- Use black-compatible import formatting
- Place module-level imports at the top of files

### Code Style (Flake8)
- Follow PEP 8 with configured exceptions:
  - Ignore E203 (whitespace before ':')
  - Ignore W503 (line break before binary operator)
  - Ignore E501 (line too long - handled by black)
- Avoid E402 errors in non-test files (imports at top)

### Type Hints (MyPy)
- Target Python 3.9.6 compatible type syntax
- Use type hints for function parameters and return values
- Avoid untyped function definitions when possible
- Use `Optional[Type]` for optional parameters (not `Type | None` - requires Python 3.10+)
- Import `Union` from `typing` for complex type unions
- Use `List[Type]`, `Dict[str, Type]` instead of built-in generics (requires Python 3.9+)
- Be explicit about return types, especially for functions that may return `Any`

### Testing Requirements
- Write testable code with clear separation of concerns
- Ensure code coverage for new functions
- Use appropriate test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Follow async/await patterns correctly for async code

### Error Handling
- Use specific exception types rather than bare `except:`
- Include proper error messages and context
- Avoid catching and ignoring exceptions without logging

### Documentation
- Include docstrings for public functions and classes
- Use clear, descriptive variable and function names
- Add type hints to improve code readability

### LangChain Specific
- Follow LangChain patterns for chain composition
- Properly handle async operations in LangChain workflows
- Use appropriate LangChain abstractions and avoid direct API calls when frameworks provide them
- Handle streaming and callback patterns correctly

## Code Generation Checklist

Before finalizing any Python code:
1. ✅ Imports are properly organized and at the top
2. ✅ Type hints are included for function signatures
3. ✅ No bare except clauses or ignored exceptions
4. ✅ Functions have appropriate docstrings
5. ✅ Code follows async/await patterns where needed
6. ✅ Variable names are descriptive and follow Python conventions
7. ✅ No unused imports or variables
8. ✅ Proper error handling with specific exception types

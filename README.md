# re-static

**Safe boilerplate-free static regular expressions with MyPy support**

`re-static` provides a powerful way to work with regular expressions in Python that gives you:
- **Type safety**: Named capture groups become typed attributes on result objects
- **IDE support**: Full autocomplete and type checking for regex groups
- **Runtime safety**: Compile-time validation of regex patterns
- **Zero runtime overhead**: Patterns are compiled once at class definition time

## Installation

```bash
pip install re-static
```

Requires Python 3.11+ and MyPy for full type checking support.

## Quick Start

```python
from re_static import StaticRegex

class EmailRegex(StaticRegex):
    REGEX = r"(?P<username>[a-zA-Z0-9._%+-]+)@(?P<domain>[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"

# Now you get type-safe access to capture groups!
match = EmailRegex.search("Contact us at hello@example.com")
if match:
    print(f"Username: {match.username}")  # Type: str
    print(f"Domain: {match.domain}")      # Type: str
```

## Features

### All Standard Regex Methods

`re-static` supports all the standard regex matching methods:

```python
class DigitsRegex(StaticRegex):
    REGEX = r"(?P<digits>\d+)"

# Match from start of string
result = DigitsRegex.match("123abc")

# Search anywhere in string
result = DigitsRegex.search("abc123def")

# Match entire string
result = DigitsRegex.fullmatch("123")

# Find all matches as a list
results = DigitsRegex.findall("123 456 789")

# Find all matches as an iterator
for result in DigitsRegex.finditer("123 456 789"):
    print(result.digits)
```

### Type-Safe Optional Groups

Optional capture groups are correctly typed as `str | None`:

```python
class OptionalRegex(StaticRegex):
    REGEX = r"(?P<required>\w+)(?P<optional>\d+)?"

match = OptionalRegex.match("hello123")
print(match.required)  # Type: str (always present)
print(match.optional)  # Type: str | None (might be None)

match = OptionalRegex.match("hello")
print(match.required)  # "hello"
print(match.optional)  # None
```

### Position and Bounds Support

All methods support the standard `pos` and `endpos` parameters:

```python
result = EmailRegex.search("prefix hello@example.com suffix", pos=7, endpos=25)
```

### Regex Flags

You can specify regex flags using the `REGEX_FLAGS` class attribute:

```python
import re

class CaseInsensitiveRegex(StaticRegex):
    REGEX = r"(?P<word>[a-z]+)"
    REGEX_FLAGS = re.IGNORECASE

match = CaseInsensitiveRegex.match("HELLO")  # Works!
print(match.word)  # "HELLO"
```

## MyPy Integration

To get full type checking support, configure MyPy to use the re-static plugin by adding this to your `pyproject.toml`:

```toml
[tool.mypy]
plugins = ["re_static.mypy_plugin.plugin"]
```

With the plugin enabled, MyPy will:
- Validate that your regex patterns are syntactically correct
- Automatically infer types for named capture groups
- Provide intelligent autocomplete in your IDE
- Catch attempts to access non-existent groups at compile time
- Enforce that regex group attributes are only accessed on instances, not classes

## Advanced Usage

### Complex Patterns

```python
class LogLineRegex(StaticRegex):
    REGEX = r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(?P<level>\w+)\] (?P<message>.*?)(?P<error_code> \(code: \d+\))?"

log_line = "2023-12-01 10:30:15 [ERROR] Database connection failed (code: 500)"
match = LogLineRegex.match(log_line)
if match:
    print(f"Time: {match.timestamp}")
    print(f"Level: {match.level}")
    print(f"Message: {match.message}")
    print(f"Error code: {match.error_code}")  # Optional group
```

## Error Handling

If a regex pattern has syntax errors, they'll be caught at class definition time:

```python
# This will raise a compile-time error:
class BadRegex(StaticRegex):
    REGEX = r"(?P<bad>[unclosed"  # SyntaxError!
```

## Performance

- Regex patterns are compiled once when the class is defined, not on each use
- Basically zero runtime overhead compared to using `re.compile()` directly
- Type checking happens at build time with MyPy, not at runtime

## Development

This project uses modern Python development practices:

- **uv** for dependency management
- **pytest** for testing
- **mypy** for type checking
- **ruff** for linting and formatting

See [development.md](development.md) for detailed development instructions.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please see our development guide and submit pull requests on GitHub.

# MyPy Plugin Testing for re-static

This directory contains comprehensive tests for the re-static mypy plugin.

## Overview

The **re-static** library provides a mypy plugin that enables type-safe regex matching by:
1. **Analyzing regex patterns** at type-check time to extract named groups
2. **Typing required groups** as `str` (always present in matches)
3. **Typing optional groups** as `str | None` (may be absent)
4. **Providing full IDE autocomplete** for regex group attributes

## Test Files

### `test_mypy_plugin_integration.yml`

**Comprehensive test suite using pytest-mypy-plugins (29 test cases)**

This is the **main and only** integration test file. It verifies:
- **Correct positives**: Valid code that should type-check successfully (13 tests)
- **Correct negatives**: Invalid code that should produce specific type errors (10 tests)
- **Edge cases**: Advanced patterns and scenarios (6 tests)

**Run with:**
```bash
uv run pytest tests/test_mypy_plugin_integration.yml -v
```

**Test Coverage:**
- ✅ Basic required groups (`str` typing)
- ✅ Optional groups (`str | None` typing)
- ✅ Type narrowing with None checks
- ✅ Return types of all match methods (match, search, fullmatch, findall, finditer)
- ✅ Error detection for:
  - Accessing attributes on None
  - Assigning `str | None` to `str` without checks
  - Wrong return type annotations
  - Missing arguments
  - Type incompatibilities
- ✅ Complex patterns with multiple optional groups
- ✅ Multiple regex classes in same scope
- ✅ Edge cases (walrus operator, list comprehensions, method chaining)

**Example test case:**
```yaml
- case: optional_group_correct_type
  mypy_config: &mypy_config |
    [mypy]
    plugins = re_static.mypy_plugin.plugin
  main: |
    from re_static import StaticRegex

    class OptionalRegex(StaticRegex):
        REGEX = r"(?P<required>[a-z]+)(?P<optional>[0-9]+)?"

    result = OptionalRegex.match("hello")
    if result:
        required: str = result.required
        optional: str | None = result.optional
        reveal_type(result.required)  # N: Revealed type is "builtins.str"
        reveal_type(result.optional)  # N: Revealed type is "builtins.str | None"
```

### `test_mypy_plugin.py`

**Unit tests for plugin internals**

Tests the plugin implementation details using mocks (separate from integration tests).

**Run with:**
```bash
uv run pytest tests/test_mypy_plugin.py -v
```

## How the Plugin Works

### 1. Class Registration

When a class inherits from `StaticRegex`, the plugin's `get_base_class_hook` is called:

```python
class EmailRegex(StaticRegex):
    REGEX = r"(?P<username>[a-zA-Z0-9._%+-]+)@(?P<domain>[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
```

The plugin:
1. Extracts the `REGEX` pattern
2. Parses it using Python's `sre_parse` module
3. Identifies all named groups and their properties:
   - Group name
   - Whether it's required (top-level) or optional (nested in optionals)
4. Registers the groups in `_class_groups` dictionary
5. Adds placeholder attributes to the class's symbol table

### 2. Attribute Type Inference

When accessing an attribute on an instance, the `get_attribute_hook` is called:

```python
result = EmailRegex.match("test@example.com")
if result:
    username = result.username  # <-- Plugin provides type here
```

The plugin:
1. Receives the `AttributeContext` with the class type info
2. Looks up the class in `_class_groups`
3. Checks if the attribute is a registered regex group
4. Returns appropriate type:
   - `str` for required groups (always present)
   - `str | None` for optional groups

### 3. Key Implementation Detail

The plugin uses the MRO (Method Resolution Order) available in `AttributeContext.type.type.mro` to check parent classes. This allows it to work with any subclass of `StaticRegex`, not just direct instances.

## Test Results

All 29 tests passing:

```
============================== 29 passed in 4.42s ===============================
```

**Test breakdown:**
- 13 positive tests (valid code)
- 10 negative tests (error detection)
- 6 edge case tests

## Adding New Tests

To add a new test case to `test_mypy_plugin_integration.yml`:

```yaml
- case: your_test_name
  mypy_config: *mypy_config  # Reuse standard config
  main: |
    from re_static import StaticRegex

    # Your test code here
    class YourRegex(StaticRegex):
        REGEX = r"(?P<group>\d+)"

    result = YourRegex.match("123")
    reveal_type(result)  # N: Revealed type is "main.YourRegex | None"
```

**Comments in test code:**
- `# N: Expected note` - Mypy should produce this note
- `# E: Expected error` - Mypy should produce this error
- `# E: Expected error  [error-code]` - Error with specific code

## Common Test Patterns

### Testing Required Groups

```python
class TestRegex(StaticRegex):
    REGEX = r"(?P<required>\w+)"

result = TestRegex.match("test")
if result:
    value: str = result.required  # Should type-check
    reveal_type(result.required)  # N: Revealed type is "builtins.str"
```

### Testing Optional Groups

```python
class TestRegex(StaticRegex):
    REGEX = r"(?P<required>\w+)(?P<optional>\d+)?"

result = TestRegex.match("test")
if result:
    req: str = result.required        # OK
    opt: str | None = result.optional # OK
    bad: str = result.optional        # E: Incompatible types  [assignment]
```

### Testing Type Narrowing

```python
if result and result.optional is not None:
    # Inside this block, mypy knows optional is str, not str | None
    upper: str = result.optional.upper()  # OK
```

## Continuous Integration

Add to your CI pipeline:

```bash
# Run comprehensive integration tests
uv run pytest tests/test_mypy_plugin_integration.yml -v

# Run unit tests for plugin internals
uv run pytest tests/test_mypy_plugin.py -v
```

## Debugging Plugin Issues

If the plugin isn't working:

1. **Check plugin is enabled** in `pyproject.toml`:
   ```toml
   [tool.mypy]
   plugins = ["re_static.mypy_plugin.plugin"]
   ```

2. **Verify plugin loads** with verbose mypy:
   ```bash
   uv run mypy --show-traceback tests/test_mypy_integration.py
   ```

3. **Use reveal_type** to see what mypy infers:
   ```python
   result = EmailRegex.match("test@example.com")
   reveal_type(result)  # Shows: EmailRegex | None
   if result:
       reveal_type(result.username)  # Shows: str or Any (if broken)
   ```

4. **Check class fullname** matches expectations:
   - The plugin registers classes by their fullname (e.g., `"main.EmailRegex"`)
   - The attribute hook checks `ctx.type.type.fullname`

## References

- [pytest-mypy-plugins documentation](https://github.com/typeddjango/pytest-mypy-plugins)
- [Mypy plugin development guide](https://mypy.readthedocs.io/en/stable/extending_mypy.html)
- [Python sre_parse module](https://github.com/python/cpython/blob/main/Lib/sre_parse.py)

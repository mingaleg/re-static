from __future__ import annotations

from unittest.mock import Mock, patch

from mypy.nodes import ClassDef, StrExpr
from mypy.options import Options
from mypy.plugin import AttributeContext, ClassDefContext
from mypy.types import Instance, NoneType, TypeType, UnionType

from re_static.analyzer import Group
from re_static.mypy_plugin.plugin import ReStaticMypyPlugin, plugin


class TestReStaticMypyPlugin:
    def setup_method(self):
        # Create a minimal Options object
        options = Options()
        self.plugin_instance = ReStaticMypyPlugin(options)
        # Clear any existing class groups between tests
        ReStaticMypyPlugin._class_groups.clear()

    def test_plugin_factory_function(self):
        plugin_class = plugin("1.0")
        assert plugin_class == ReStaticMypyPlugin

    def test_get_base_class_hook_returns_hook_for_static_regex(self):
        hook = self.plugin_instance.get_base_class_hook("re_static_mypy.static_regex.StaticRegex")
        assert hook is not None
        assert hook == self.plugin_instance._static_regex_class_hook

    def test_get_base_class_hook_returns_none_for_other_classes(self):
        hook = self.plugin_instance.get_base_class_hook("some.other.Class")
        assert hook is None

    def test_get_attribute_hook_returns_none_for_non_static_regex(self):
        hook = self.plugin_instance.get_attribute_hook("some.other.class.attribute")
        assert hook is None

    def test_get_attribute_hook_returns_hook_for_group_attribute(self):
        # Set up mock group data
        self.plugin_instance._class_groups["test.class"] = [
            Group(index=1, name="test_group", always_present=True)
        ]

        hook = self.plugin_instance.get_attribute_hook(
            "re_static_mypy.static_regex.StaticRegex.test_group"
        )
        assert hook is not None
        assert hook == self.plugin_instance._attribute_hook


class TestStaticRegexClassHook:
    def setup_method(self):
        # Create a minimal Options object
        options = Options()
        self.plugin_instance = ReStaticMypyPlugin(options)
        ReStaticMypyPlugin._class_groups.clear()

    def create_mock_context_with_regex(self, regex_pattern: str):
        """Helper to create a mock ClassDefContext with a REGEX pattern"""
        context = Mock(spec=ClassDefContext)

        # Create mock class definition
        cls = Mock(spec=ClassDef)
        context.cls = cls

        # Create mock class info
        cls.info = Mock()
        cls.info.fullname = "test.TestClass"
        cls.info.names = {}

        # Create mock statement with REGEX assignment
        stmt = Mock()
        stmt.lvalues = [Mock()]
        stmt.lvalues[0].name = "REGEX"
        stmt.rvalue = StrExpr(regex_pattern)

        cls.defs = Mock()
        cls.defs.body = [stmt]

        return context

    @patch("re_static.mypy_plugin.plugin.get_groups")
    def test_static_regex_class_hook_with_valid_regex(self, mock_get_groups):
        # Setup mock
        mock_groups = [
            Group(index=0, name=None, always_present=True),
            Group(index=1, name="digits", always_present=True),
            Group(index=2, name="letter", always_present=False),
        ]
        mock_get_groups.return_value = mock_groups

        context = self.create_mock_context_with_regex(r"(?P<digits>\d+)(?P<letter>[a-z])?")

        # Mock the necessary mypy types and nodes
        with (
            patch("mypy.nodes.Var") as mock_var,
            patch("mypy.nodes.SymbolTableNode") as mock_symbol_node,
            patch("mypy.types.AnyType") as mock_any_type,
            patch("mypy.nodes.MDEF"),
        ):
            mock_any_type.return_value = Mock()
            mock_var_instance = Mock()
            mock_var.return_value = mock_var_instance
            mock_symbol_node.return_value = Mock()

            # Call the hook
            self.plugin_instance._static_regex_class_hook(context)

            # Verify groups were stored
            assert "test.TestClass" in self.plugin_instance._class_groups
            assert self.plugin_instance._class_groups["test.TestClass"] == mock_groups

            # Verify get_groups was called with correct parameters
            mock_get_groups.assert_called_once_with(r"(?P<digits>\d+)(?P<letter>[a-z])?", flags=0)

    def test_static_regex_class_hook_with_no_regex(self):
        context = Mock(spec=ClassDefContext)
        cls = Mock(spec=ClassDef)
        context.cls = cls
        cls.defs = Mock()
        cls.defs.body = []  # No REGEX definition

        self.plugin_instance._static_regex_class_hook(context)

        # Should not add anything to class_groups
        assert len(self.plugin_instance._class_groups) == 0

    @patch("re_static.mypy_plugin.plugin.get_groups")
    def test_static_regex_class_hook_with_invalid_regex(self, mock_get_groups):
        # Setup mock to raise exception
        mock_get_groups.side_effect = Exception("Invalid regex")

        context = self.create_mock_context_with_regex(r"[invalid")

        # Should not crash and not add to class_groups
        self.plugin_instance._static_regex_class_hook(context)
        assert len(self.plugin_instance._class_groups) == 0


class TestAttributeHook:
    def setup_method(self):
        # Create a minimal Options object
        options = Options()
        self.plugin_instance = ReStaticMypyPlugin(options)
        ReStaticMypyPlugin._class_groups.clear()

    def create_mock_attribute_context(self, attr_name: str, is_class_access: bool = False):
        """Helper to create mock AttributeContext"""
        context = Mock(spec=AttributeContext)
        context.context = Mock()
        context.context.name = attr_name
        context.default_attr_type = Mock()
        context.api = Mock()

        if is_class_access:
            # Mock class access (TypeType)
            context.type = Mock(spec=TypeType)
            context.type.item = Mock(spec=Instance)
            context.type.item.type = Mock()
            context.type.item.type.fullname = "test.TestClass"
            context.type.item.type.name = "TestClass"
        else:
            # Mock instance access
            context.type = Mock(spec=Instance)
            context.type.type = Mock()
            context.type.type.fullname = "test.TestClass"

        return context

    def test_attribute_hook_class_access_to_group_attribute_fails(self):
        # Setup group data
        self.plugin_instance._class_groups["test.TestClass"] = [
            Group(index=1, name="test_group", always_present=True)
        ]

        context = self.create_mock_attribute_context("test_group", is_class_access=True)

        result = self.plugin_instance._attribute_hook(context)

        # Should call api.fail
        context.api.fail.assert_called_once()
        error_message = context.api.fail.call_args[0][0]
        assert "test_group" in error_message
        assert "instance attribute" in error_message
        assert result == context.default_attr_type

    def test_attribute_hook_instance_access_always_present_group(self):
        # Setup group data
        self.plugin_instance._class_groups["test.TestClass"] = [
            Group(index=1, name="test_group", always_present=True)
        ]

        context = self.create_mock_attribute_context("test_group", is_class_access=False)

        # Mock the string type creation
        mock_str_type = Mock()
        context.api.named_generic_type.return_value = mock_str_type

        result = self.plugin_instance._attribute_hook(context)

        # Should return string type for always present group
        context.api.named_generic_type.assert_called_once_with("builtins.str", [])
        assert result == mock_str_type

    def test_attribute_hook_instance_access_optional_group(self):
        # Setup group data
        self.plugin_instance._class_groups["test.TestClass"] = [
            Group(index=1, name="test_group", always_present=False)
        ]

        context = self.create_mock_attribute_context("test_group", is_class_access=False)
        context.context.line = 42  # Mock line number for UnionType

        # Mock the type creation
        mock_str_type = Mock()
        mock_none_type = Mock(spec=NoneType)
        mock_union_type = Mock(spec=UnionType)

        context.api.named_generic_type.return_value = mock_str_type

        with (
            patch("mypy.types.NoneType", return_value=mock_none_type),
            patch("mypy.types.UnionType", return_value=mock_union_type) as mock_union_constructor,
        ):
            result = self.plugin_instance._attribute_hook(context)

            # Should create UnionType of str and None
            mock_union_constructor.assert_called_once_with([mock_str_type, mock_none_type], line=42)
            assert result == mock_union_type

    def test_attribute_hook_non_group_attribute(self):
        # Setup group data (but for different attribute)
        self.plugin_instance._class_groups["test.TestClass"] = [
            Group(index=1, name="other_group", always_present=True)
        ]

        context = self.create_mock_attribute_context("non_group_attr", is_class_access=False)

        result = self.plugin_instance._attribute_hook(context)

        # Should return default type for non-group attributes
        assert result == context.default_attr_type

    def test_attribute_hook_unknown_class(self):
        context = self.create_mock_attribute_context("some_attr", is_class_access=False)
        context.type.type.fullname = "unknown.Class"

        result = self.plugin_instance._attribute_hook(context)

        # Should return default type for unknown classes
        assert result == context.default_attr_type

    def test_attribute_hook_fallback_to_default(self):
        context = Mock(spec=AttributeContext)
        context.context = Mock()
        # No name or member attribute to simulate edge case
        context.default_attr_type = Mock()

        result = self.plugin_instance._attribute_hook(context)

        assert result == context.default_attr_type

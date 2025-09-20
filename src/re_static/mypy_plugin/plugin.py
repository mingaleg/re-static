from collections.abc import Callable
from typing import ClassVar

from mypy.nodes import StrExpr
from mypy.plugin import AttributeContext, ClassDefContext, Plugin
from mypy.types import Type

from re_static.analyzer import Group, get_groups


class ReStaticMypyPlugin(Plugin):
    # Store group information for each class
    _class_groups: ClassVar[dict[str, list[Group]]] = {}

    def get_base_class_hook(self, fullname: str) -> Callable[[ClassDefContext], None] | None:
        if fullname == "re_static_mypy.static_regex.StaticRegex":
            return self._static_regex_class_hook
        return None

    def get_attribute_hook(self, fullname: str) -> Callable[[AttributeContext], Type] | None:
        # Only hook into specific StaticRegex subclass attributes
        if fullname.startswith("re_static_mypy.static_regex.StaticRegex") and "." in fullname:
            attr_name = fullname.split(".")[-1]
            # Check if this could be a regex group attribute
            for groups in self._class_groups.values():
                for group in groups:
                    if group.name == attr_name:
                        return self._attribute_hook
        return None

    def _static_regex_class_hook(self, ctx: ClassDefContext) -> None:
        """Hook called when a class inherits from StaticRegex"""
        from mypy.nodes import MDEF, SymbolTableNode, Var
        from mypy.types import AnyType, TypeOfAny

        cls = ctx.cls

        # Look for REGEX class variable in the class definition
        regex_pattern = None
        for stmt in cls.defs.body:
            if hasattr(stmt, "lvalues") and stmt.lvalues:
                for lvalue in stmt.lvalues:
                    if hasattr(lvalue, "name") and lvalue.name == "REGEX":
                        if hasattr(stmt, "rvalue") and isinstance(stmt.rvalue, StrExpr):
                            regex_pattern = stmt.rvalue.value
                            break
            elif hasattr(stmt, "name") and stmt.name == "REGEX":
                if hasattr(stmt, "rvalue") and isinstance(stmt.rvalue, StrExpr):
                    regex_pattern = stmt.rvalue.value
                    break

        if not regex_pattern:
            return

        try:
            groups = get_groups(regex_pattern, flags=0)
            # Store group info for this class
            class_fullname = cls.info.fullname
            self._class_groups[class_fullname] = groups
        except Exception:
            return

        # Get the TypeInfo for this class
        class_type_info = cls.info

        # Add group attributes to this specific class with Any type
        # The attribute hook will provide the proper types and handle class vs instance access
        any_type = AnyType(TypeOfAny.special_form)

        for group in groups:
            if group.index == 0 or not group.name:
                continue

            # Create a variable for this group attribute
            var = Var(group.name, any_type)
            var.info = class_type_info
            var._fullname = f"{class_type_info.fullname}.{group.name}"

            # Add to the class's symbol table
            symbol_node = SymbolTableNode(kind=MDEF, node=var)
            class_type_info.names[group.name] = symbol_node

    def _attribute_hook(self, ctx: AttributeContext) -> Type:
        """Provide proper types for regex group attributes and enforce instance-only access"""
        from mypy.types import Instance, NoneType, TypeType, UnionType

        # Get the attribute name
        if hasattr(ctx.context, "name"):
            attr_name = ctx.context.name
        elif hasattr(ctx.context, "member"):
            attr_name = ctx.context.member
        else:
            return ctx.default_attr_type

        # Check if this is a class access (type[SomeClass].attribute)
        if isinstance(ctx.type, TypeType):
            # This is class attribute access (e.g., StaticRegexFoo.digits)
            if isinstance(ctx.type.item, Instance):
                class_fullname = ctx.type.item.type.fullname
                if class_fullname in self._class_groups:
                    groups = self._class_groups[class_fullname]
                    # Check if this is a group attribute
                    for group in groups:
                        if group.name == attr_name:
                            # This is a regex group attribute being accessed on the class
                            ctx.api.fail(
                                f'"{attr_name}" is an instance attribute for regex groups, '
                                f"not a class attribute. Use an instance of {ctx.type.item.type.name} instead.",
                                ctx.context,
                            )
                            return ctx.default_attr_type

        # Handle instance attribute access
        elif isinstance(ctx.type, Instance):
            class_fullname = ctx.type.type.fullname

            # Check if we have group information for this class
            if class_fullname in self._class_groups:
                groups = self._class_groups[class_fullname]

                # Look for this attribute in the groups
                for group in groups:
                    if group.name == attr_name:
                        api = ctx.api
                        str_type = api.named_generic_type("builtins.str", [])

                        if group.always_present:
                            return str_type
                        else:
                            none_type = NoneType()
                            return UnionType([str_type, none_type], line=ctx.context.line)

        return ctx.default_attr_type


def plugin(version: str) -> type[ReStaticMypyPlugin]:
    return ReStaticMypyPlugin

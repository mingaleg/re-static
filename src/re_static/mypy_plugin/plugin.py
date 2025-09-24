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
        if fullname == "re_static.re_static.StaticRegex":
            return self._static_regex_class_hook
        return None

    def get_attribute_hook(self, fullname: str) -> Callable[[AttributeContext], Type] | None:
        # Return the hook for any attribute access - let _attribute_hook do the filtering
        # _attribute_hook will check if the class is a registered StaticRegex subclass
        if "." in fullname:
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
            if lvalues := getattr(stmt, "lvalues", None):
                for lvalue in lvalues:
                    if getattr(lvalue, "name", None) == "REGEX" and isinstance(
                        rvalue := getattr(stmt, "rvalue", None), StrExpr
                    ):
                        regex_pattern = rvalue.value
                        break
            elif getattr(stmt, "name", None) == "REGEX" and isinstance(
                rvalue := getattr(stmt, "rvalue", None), StrExpr
            ):
                regex_pattern = rvalue.value
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
        if not (attr_name := getattr(ctx.context, "name", None)):
            if not (attr_name := getattr(ctx.context, "member", None)):
                return ctx.default_attr_type

        # Check if this is a class access (type[SomeClass].attribute)
        if isinstance(ctx.type, TypeType):
            # This is class attribute access (e.g., StaticRegexFoo.digits)
            if isinstance(ctx.type.item, Instance):
                # Walk the MRO to find if this is a regex group attribute
                for base_class in ctx.type.item.type.mro:
                    if groups := self._class_groups.get(base_class.fullname):
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
            # Walk the MRO to find regex groups in this class or any parent class
            for base_class in ctx.type.type.mro:
                # Check if this class in the MRO has registered groups
                if groups := self._class_groups.get(base_class.fullname):
                    # Look for this attribute in the groups
                    for group in groups:
                        if group.name == attr_name:
                            str_type = ctx.api.named_generic_type("builtins.str", [])

                            if group.always_present:
                                return str_type
                            else:
                                return UnionType([str_type, NoneType()], line=ctx.context.line)

        return ctx.default_attr_type


def plugin(version: str) -> type[ReStaticMypyPlugin]:
    return ReStaticMypyPlugin

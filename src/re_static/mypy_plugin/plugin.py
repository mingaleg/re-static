from collections.abc import Callable
from typing import ClassVar

from mypy.nodes import StrExpr
from mypy.plugin import AttributeContext, ClassDefContext, Plugin
from mypy.types import Type

from re_static.analyzer import Group, get_groups


class ReStaticMypyPlugin(Plugin):
    _class_groups: ClassVar[dict[str, list[Group]]] = {}

    def get_base_class_hook(self, fullname: str) -> Callable[[ClassDefContext], None] | None:
        if fullname == "re_static.re_static.StaticRegex":
            return self._static_regex_class_hook
        return None

    def get_attribute_hook(self, fullname: str) -> Callable[[AttributeContext], Type] | None:
        # Filtering happens in _attribute_hook, not here
        if "." in fullname:
            return self._attribute_hook
        return None

    def _static_regex_class_hook(self, ctx: ClassDefContext) -> None:
        from mypy.nodes import MDEF, SymbolTableNode, Var
        from mypy.types import AnyType, TypeOfAny

        cls = ctx.cls
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
            class_fullname = cls.info.fullname
            self._class_groups[class_fullname] = groups
        except Exception as exc:
            ctx.api.fail(f'Invalid regex pattern: {exc}', ctx.cls)
            return

        class_type_info = cls.info

        # Placeholders; the attribute hook will provide the proper types
        any_type = AnyType(TypeOfAny.special_form)

        for group in groups:
            if group.index == 0 or not group.name:
                continue

            var = Var(group.name, any_type)
            var.info = class_type_info
            var._fullname = f"{class_type_info.fullname}.{group.name}"
            symbol_node = SymbolTableNode(kind=MDEF, node=var)
            class_type_info.names[group.name] = symbol_node

    def _attribute_hook(self, ctx: AttributeContext) -> Type:
        from mypy.types import Instance, NoneType, TypeType, UnionType

        if not (attr_name := getattr(ctx.context, "name", None)):
            if not (attr_name := getattr(ctx.context, "member", None)):
                return ctx.default_attr_type

        if isinstance(ctx.type, TypeType):
            # Reject class-level access to group attributes (e.g. MyRegex.digits)
            if isinstance(ctx.type.item, Instance):
                for base_class in ctx.type.item.type.mro:
                    if groups := self._class_groups.get(base_class.fullname):
                        for group in groups:
                            if group.name == attr_name:
                                ctx.api.fail(
                                    f'"{attr_name}" is an instance attribute for regex groups, '
                                    f"not a class attribute. Use an instance of {ctx.type.item.type.name} instead.",
                                    ctx.context,
                                )
                                return ctx.default_attr_type

        elif isinstance(ctx.type, Instance):
            for base_class in ctx.type.type.mro:
                if groups := self._class_groups.get(base_class.fullname):
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

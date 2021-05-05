import warnings
from dataclasses import dataclass
from typing import Callable, Dict, NamedTuple, Optional, TypeVar, Union

from apischema.types import AnyType, PRIMITIVE_TYPES
from apischema.typing import get_args, get_origin
from apischema.utils import contains, has_type_vars, is_type_var, replace_builtins


class TypeName(NamedTuple):
    json_schema: Optional[str]
    graphql: Optional[str]


NameOrFactory = Union[str, None, Callable[..., Optional[str]]]


def _apply_args(name_or_factory: NameOrFactory, *args) -> Optional[str]:
    return name_or_factory(*args) if callable(name_or_factory) else name_or_factory


_type_names: Dict[AnyType, "TypeNameFactory"] = {}

T = TypeVar("T")


@dataclass(frozen=True)
class TypeNameFactory:
    json_schema: NameOrFactory
    graphql: NameOrFactory

    def __call__(self, tp: T) -> T:
        self.check_type(tp)
        _type_names[replace_builtins(tp)] = self
        return tp

    def check_type(self, tp: AnyType):
        if is_type_var(tp):
            raise TypeError("TypeVar cannot have a type_name")
        if has_type_vars(tp):
            if get_args(tp):
                raise TypeError("Generic alias cannot have a type_name")
            elif isinstance(self.json_schema, str) or isinstance(self.graphql, str):
                raise TypeError(
                    "Unspecialized generic type must used factory type_name"
                )

    def to_type_name(self, tp: AnyType, *args) -> TypeName:
        self.check_type(tp)
        return TypeName(
            _apply_args(self.json_schema, tp, *args),
            _apply_args(self.graphql, tp, *args),
        )


def type_name(
    ref: NameOrFactory = None,
    *,
    json_schema: NameOrFactory = None,
    graphql: NameOrFactory = None,
) -> TypeNameFactory:
    return TypeNameFactory(json_schema or ref, graphql or ref)


def _default_type_name(tp: AnyType) -> TypeName:
    if (
        hasattr(tp, "__name__")
        and not get_args(tp)
        and not has_type_vars(tp)
        and tp not in PRIMITIVE_TYPES
    ):
        return TypeName(tp.__name__, tp.__name__)
    else:
        return TypeName(None, None)


def get_type_name(tp: AnyType) -> TypeName:
    tp = replace_builtins(tp)
    if contains(_type_names, tp):
        return _type_names[tp].to_type_name(tp)
    origin, args = get_origin(tp), get_args(tp)
    if args and not has_type_vars(tp) and contains(_type_names, origin):
        return _type_names[origin].to_type_name(origin, *args)
    return _default_type_name(tp)


def schema_ref(ref: Optional[str]) -> Callable[[T], T]:
    warnings.warn("schema_ref is deprecated, use type_name instead", DeprecationWarning)
    return type_name(ref)
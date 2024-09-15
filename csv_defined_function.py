import csv
from dataclasses import dataclass, fields, is_dataclass
from functools import reduce
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Literal,
    TypeVar,
    cast,
    get_args,
    get_origin,
)


class WithWildcards: ...


class Wildcard:
    def __repr__(self) -> str:
        return "*"

    def __eq__(self, other: Any) -> Any:
        return True


Flavour = Literal["vanilla", "strawberry", "chocolate", "ants"]


@dataclass(frozen=True)
class IceCreamName:
    brand_name: str
    edition: str


@dataclass(frozen=True)
class IceCream:
    full_name: IceCreamName
    flavour: Flavour
    zip_code: int


@dataclass(frozen=True)
class Product:
    product_id: str
    company: str
    jurisdiction_id: int
    reviews: Literal["bad", "good"]


S = TypeVar("S")
T = TypeVar("T")


def parse(cell: str, as_type: type[S]) -> S:
    if cell == "*":
        return cast(S, Wildcard())
    if as_type is str:
        # Return straight
        return cast(S, cell)
    if as_type is int:
        # Convert to int
        return cast(S, int(cell))
    if get_origin(as_type) is Literal:
        # Convert to the type of each value
        # and return the one that's equal to
        # the Literal member
        for value in get_args(as_type):
            converted_cell = type(value)(cell)
            if converted_cell == value:
                return converted_cell

        raise ValueError(f"'{cell}' is not in {get_args(as_type)}")

    raise ValueError(f"Don't know how to deal with type {as_type}")


@dataclass(frozen=True)
class CSVDeserialiser(Generic[T]):
    row_type: type[T]

    @classmethod
    def parse_row(cls, row: dict[str, str], as_type: type[S]) -> S:
        if get_origin(as_type) is tuple:
            return cast(
                S,
                tuple(
                    cls.parse_row(row, tuple_type) for tuple_type in get_args(as_type)
                ),
            )
        elif is_dataclass(as_type):
            return as_type(
                **{
                    field.name: (
                        cls.parse_row(row, field.type)
                        if is_dataclass(field.type)
                        else (
                            parse(row[field.name], field.type)
                            if field.name in row
                            else cast(S, Wildcard())
                        )
                    )
                    for field in fields(as_type)
                }
            )

        raise ValueError(f"Can't work with type {as_type}")

    def load(self, path: Path) -> Iterator[T]:
        with path.open() as f:
            for row in csv.DictReader(f):
                for key in row:
                    assert key.strip() == key, f"No whitespace allowed in key '{key}'"
                yield self.parse_row(row, self.row_type)


# Secretly involves wildcards, maybe should be TopologicalBinaryRelation
# or whatever it's actually called in maths when it's subsets
# instead of elements
BinaryRelation = Iterable[
    tuple[Annotated[S, WithWildcards], Annotated[T, WithWildcards]]
]


def check_relation_is_function(binary_relation: BinaryRelation[S, T]) -> None:
    collected_relation = tuple(binary_relation)
    for i in range(len(collected_relation)):
        first_domain, first_range = collected_relation[i]
        for j in range(i + 1, len(collected_relation)):
            second_domain, second_range = collected_relation[j]
            assert not (
                # Due to the presence (and interpretation) of `Wildcard`s, this
                # statement is really equivalent to the domains overlapping
                # and the ranges not overlapping. So you can't define
                # a function satisfying both mappings.
                first_domain == second_domain
                and first_range != second_range
            ), (
                f"{first_domain} and {second_domain} are compatible"
                f" (overlap) but their respective mappings"
                f" {first_range} and {second_range} conflict"
            )


def intersection(
    the_type: type[T], instances: Iterable[Annotated[T, WithWildcards]]
) -> Annotated[T, WithWildcards]:
    if not is_dataclass(the_type):
        def accumulate(acc: T, v: T):
            if isinstance(v, Wildcard):
                return acc
            else:
                assert isinstance(acc, Wildcard) or acc == v
                return v

        return reduce(accumulate, instances, Wildcard())
    else:
        return the_type(
            **{
                field.name: intersection(
                    field.type, (getattr(instance, field.name) for instance in instances)
                )
                for field in fields(the_type)
            }
        )


def to_function(
    binary_relation: BinaryRelation[S, T]
) -> Callable[[Annotated[S, WithWildcards]], Annotated[T, WithWildcards]]:
    collected_relation = tuple(binary_relation)

    check_relation_is_function(collected_relation)

    def fn(s: Annotated[S, WithWildcards]) -> Annotated[T, WithWildcards]:
        return intersection(
            # Assumes dataclass that's not wildcard at the top
            type(collected_relation[0][1]),
            tuple(range for domain, range in collected_relation if domain == s),
        )

    return fn

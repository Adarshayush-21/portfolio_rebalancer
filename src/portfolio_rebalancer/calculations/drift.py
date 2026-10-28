
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AllocationDrift:
    asset_class: str
    actual_weight: Decimal
    target_weight: Decimal
    drift: Decimal
    recommended_direction: str


def calculate_allocation_drift(
    actual_allocations: dict[str, Decimal],
    target_allocations: dict[str, Decimal],
    tolerance: Decimal = Decimal("0.01"),
) -> list[AllocationDrift]:
    if tolerance < 0:
        raise ValueError("tolerance cannot be negative")

    asset_classes = sorted(set(actual_allocations) | set(target_allocations))
    results: list[AllocationDrift] = []

    for asset_class in asset_classes:
        actual = actual_allocations.get(asset_class, Decimal("0"))
        target = target_allocations.get(asset_class, Decimal("0"))
        drift = actual - target

        if drift > tolerance:
            direction = "REDUCE"
        elif drift < -tolerance:
            direction = "INCREASE"
        else:
            direction = "HOLD"

        results.append(
            AllocationDrift(
                asset_class=asset_class,
                actual_weight=actual,
                target_weight=target,
                drift=drift,
                recommended_direction=direction,
            )
        )

    return results

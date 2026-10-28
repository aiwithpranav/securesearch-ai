"""The synthetic people of the scale demo (pure, deterministic: the same seed gives the same people).

They share the demo password from SEED_USER_PASSWORD (the loader hashes it once). Emails look like big0001@demo."""
import random
from dataclasses import dataclass
from typing import Any

DEPARTMENT_WEIGHTS: list[tuple[str, int]] = [
    ("Engineering", 35), ("Sales", 15), ("Customer Support", 15), ("Company-wide", 13),
    ("Finance", 8), ("HR", 5), ("Security", 5), ("Legal", 4),
]
DEPARTMENT_ROLE = {
    "Engineering": "engineer", "HR": "hr_manager", "Finance": "finance_analyst",
    "Sales": "sales_executive", "Security": "security_admin",
}
CLEARANCE_WEIGHTS = [(0, 5), (1, 45), (2, 30), (3, 15), (4, 5)]
COUNTRIES = [("IN", 80), ("US", 12), ("DE", 5), ("GB", 3)]
EXECUTIVE_SHARE = 0.02


@dataclass(frozen=True)
class PersonSpec:
    email: str
    full_name: str
    department: str
    clearance: int
    country: str
    roles: tuple[str, ...]


def _pick(rng: random.Random, weighted: list[tuple[Any, int]]) -> Any:
    return rng.choices([w[0] for w in weighted], weights=[w[1] for w in weighted])[0]


def make_people(count: int, seed: int = 10) -> list[PersonSpec]:
    rng = random.Random(seed)
    people = []
    for n in range(1, count + 1):
        department = _pick(rng, DEPARTMENT_WEIGHTS)
        roles = ["employee"]
        if department in DEPARTMENT_ROLE:
            roles.append(DEPARTMENT_ROLE[department])
        if rng.random() < EXECUTIVE_SHARE:
            roles.append("executive")
        people.append(PersonSpec(
            email=f"big{n:04d}@demo", full_name=f"Scale Demo {n:04d}", department=department,
            clearance=_pick(rng, CLEARANCE_WEIGHTS), country=_pick(rng, COUNTRIES), roles=tuple(roles),
        ))
    return people

from typing import Annotated, Literal

from pydantic import StringConstraints

# Simple email shape check (something@something). We avoid strict validators on
# purpose: the demo accounts use "swara@demo", which has no ".com" part.
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+$",
    ),
]

# Length limits stop someone sending a 10 MB "password" to burn CPU in the hasher.
NewPassword = Annotated[str, StringConstraints(min_length=12, max_length=128)]
AnyPassword = Annotated[str, StringConstraints(min_length=1, max_length=128)]

EmploymentType = Literal["full_time", "part_time", "contractor", "intern"]

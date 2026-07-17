from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Usuario:
    id: Optional[int]
    username: str = ''
    first_name: str = ''
    last_name: str = ''
    email: str = ''
    is_active: bool = True
    is_superuser: bool = False
    is_staff: bool = False
    grupos: List[str] = field(default_factory=list)
    password_hash: Optional[str] = None

    @property
    def nombre_completo(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username

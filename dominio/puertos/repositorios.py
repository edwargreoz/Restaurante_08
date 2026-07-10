from typing import Optional, Protocol
from dominio.entidades.comanda import Comanda

class IComandaRepository(Protocol):
    def obtener_por_id(self, comanda_id: int) -> Optional[Comanda]:
        ...

    def guardar(self, comanda: Comanda) -> Comanda:
        ...

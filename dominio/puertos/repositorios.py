from typing import Optional, Protocol, List
from dominio.entidades.comanda import Comanda
from dominio.entidades.mesa import Mesa
from dominio.entidades.reserva import Reserva
from dominio.entidades.plato import Plato
from dominio.entidades.insumo import Insumo
from dominio.entidades.caja import Caja
from dominio.entidades.linea_comanda import LineaComanda


class IComandaRepository(Protocol):
    def obtener_por_id(self, comanda_id: int) -> Optional[Comanda]: 
        ...
    def guardar(self, comanda: Comanda) -> Comanda: 
        ...
class IMesaRepository(Protocol):
    def obtener_por_id(self,mesa_id: int) -> Optional[Mesa]:
        ...
    def guardar(self, mesa:Mesa)-> Mesa:
        ...
    def listar_activas(self)-> List[Mesa]:
        ...
    
class IReservaRepository(Protocol):
    def obtener_por_id(self, reserva_id: int)-> Optional[Reserva]:
        ...
    def guardar(self, reserva: Reserva) -> Reserva: ...

class IPlatoRepository(Protocol):
    def obtener_por_id(self, plato_id : int ) -> Optional[Plato]:
        ...

class IInsumoRepository(Protocol):
    def obtener_por_id(self, insumo_id: int) -> Optional[Insumo]: 
        ...
    def guardar(self, insumo: Insumo) -> Insumo: ...


class ICajaRepository(Protocol):
    def obtener_abierta(self) -> Optional[Caja]: 
        ...
    def guardar(self, caja: Caja) -> Caja: 
        ...
    
    

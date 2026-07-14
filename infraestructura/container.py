from infraestructura.persistencia.repositorios.comanda_repo import ComandaRepository
from infraestructura.persistencia.repositorios.mesa_repo import MesaRepository
from infraestructura.persistencia.repositorios.reserva_repo import ReservaRepository
from infraestructura.persistencia.repositorios.plato_repo import PlatoRepository
from infraestructura.persistencia.repositorios.insumo_repo import InsumoRepository
from infraestructura.persistencia.repositorios.caja_repo import CajaRepository
from infraestructura.persistencia.repositorios.pago_repo import PagoRepository
from infraestructura.persistencia.repositorios.linea_comanda_repo import LineaComandaRepository
from infraestructura.persistencia.repositorios.categoria_repo import CategoriaRepository


class Container:
    def __init__(self):
        self.comanda_repo = ComandaRepository()
        self.mesa_repo = MesaRepository()
        self.reserva_repo = ReservaRepository()
        self.plato_repo = PlatoRepository()
        self.insumo_repo = InsumoRepository()
        self.caja_repo = CajaRepository()
        self.pago_repo = PagoRepository()
        self.linea_comanda_repo = LineaComandaRepository()
        self.categoria_repo = CategoriaRepository()


_container = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container
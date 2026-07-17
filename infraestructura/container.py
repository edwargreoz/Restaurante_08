from infraestructura.persistencia.repositorios.comanda_repo import ComandaRepository
from infraestructura.persistencia.repositorios.mesa_repo import MesaRepository
from infraestructura.persistencia.repositorios.reserva_repo import ReservaRepository
from infraestructura.persistencia.repositorios.plato_repo import PlatoRepository
from infraestructura.persistencia.repositorios.insumo_repo import InsumoRepository
from infraestructura.persistencia.repositorios.caja_repo import CajaRepository
from infraestructura.persistencia.repositorios.pago_repo import PagoRepository
from infraestructura.persistencia.repositorios.linea_comanda_repo import LineaComandaRepository
from infraestructura.persistencia.repositorios.categoria_repo import CategoriaRepository
from infraestructura.persistencia.repositorios.union_mesa_repo import UnionMesaRepository
from infraestructura.persistencia.repositorios.movimiento_insumo_repo import MovimientoInsumoRepository
from infraestructura.persistencia.repositorios.unidad_conversion_repo import UnidadConversionRepository
from infraestructura.persistencia.repositorios.receta_repo import RecetaRepository
from infraestructura.persistencia.repositorios.usuario_repo import UsuarioRepository


from menu.services import CategoriaService, PlatoService
from mesas.services import MesaService, UnionMesaService
from pedidos.services import ComandaService, LineaComandaService
from inventario.services import InsumoService, RecetaService, UnidadConversionService
from caja.services import CajaService, PagoService, ReporteService
from reservas.services import ReservaService
from core.services import DashboardService, UsuarioService


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
        self.union_mesa_repo = UnionMesaRepository()
        self.movimiento_insumo_repo = MovimientoInsumoRepository()
        self.unidad_conversion_repo = UnidadConversionRepository()
        self.receta_repo = RecetaRepository()
        self.usuario_repo = UsuarioRepository()

        self.categoria_service = CategoriaService(
            categoria_repo=self.categoria_repo
        )
        self.plato_service = PlatoService(
            plato_repo=self.plato_repo,
            categoria_repo=self.categoria_repo,
            receta_repo=self.receta_repo,
        )
        self.mesa_service = MesaService(
            mesa_repo=self.mesa_repo,
            comanda_repo=self.comanda_repo,
            reserva_repo=self.reserva_repo,
            union_mesa_repo=self.union_mesa_repo,
        )
        self.union_mesa_service = UnionMesaService(
            mesa_repo=self.mesa_repo,
            comanda_repo=self.comanda_repo,
            union_mesa_repo=self.union_mesa_repo,
        )

        self.insumo_service = InsumoService(
            insumo_repo=self.insumo_repo,
            unidad_conversion_repo=self.unidad_conversion_repo,
            movimiento_insumo_repo=self.movimiento_insumo_repo,
        )
        self.unidad_conversion_service = UnidadConversionService(
            unidad_conversion_repo=self.unidad_conversion_repo,
        )

        self.receta_service = RecetaService(
            receta_repo=self.receta_repo,
            insumo_repo=self.insumo_repo,
        )

        self.reserva_service = ReservaService(
            reserva_repo=self.reserva_repo,
            mesa_repo=self.mesa_repo,
            union_mesa_repo=self.union_mesa_repo,
        )

        self.comanda_service = ComandaService(
            comanda_repo=self.comanda_repo,
            mesa_repo=self.mesa_repo,
            caja_repo=self.caja_repo,
            union_mesa_repo=self.union_mesa_repo,
            reserva_repo=self.reserva_repo,
            reserva_service=self.reserva_service,
            linea_comanda_repo=self.linea_comanda_repo,
            pago_repo=self.pago_repo,
            plato_repo=self.plato_repo,
            receta_repo=self.receta_repo,
            insumo_repo=self.insumo_repo,
            movimiento_insumo_repo=self.movimiento_insumo_repo,
            categoria_repo=self.categoria_repo,
        )

        self.linea_comanda_service = LineaComandaService(
            linea_comanda_repo=self.linea_comanda_repo,
            comanda_repo=self.comanda_repo,
        )
        self.caja_service = CajaService(
            caja_repo=self.caja_repo,
            comanda_repo=self.comanda_repo,
            pago_repo=self.pago_repo,
        )
        self.pago_service = PagoService(
            comanda_service=self.comanda_service,
            comanda_repo=self.comanda_repo,
            pago_repo=self.pago_repo,
        )

        self.dashboard_service = DashboardService(
            mesa_repo=self.mesa_repo,
            comanda_repo=self.comanda_repo,
            insumo_repo=self.insumo_repo,
            caja_repo=self.caja_repo,
            pago_repo=self.pago_repo,
        )
        self.usuario_service = UsuarioService(usuario_repo=self.usuario_repo)

        self.reporte_service = ReporteService(
            pago_service=self.pago_service,
            insumo_repo=self.insumo_repo,
            linea_comanda_repo=self.linea_comanda_repo,
        )

import threading

_container = None
_lock = threading.Lock()


def get_container() -> Container:
    global _container
    if _container is None:
        with _lock:
            if _container is None:
                _container = Container()
    return _container

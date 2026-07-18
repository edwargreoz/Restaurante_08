from decimal import Decimal
from datetime import datetime, timezone, timedelta
from core.excepciones import RecursoNoEncontrado, ReglaNegocioViolada
from dominio.puertos.repositorios import (
    IMesaRepository, IComandaRepository, IInsumoRepository,
    ICajaRepository, IPagoRepository, IUsuarioRepository,
)


class DashboardService:
    """Datos agregados para el dashboard segun el rol del usuario."""

    def __init__(self, mesa_repo: IMesaRepository,
                 comanda_repo: IComandaRepository,
                 insumo_repo: IInsumoRepository,
                 caja_repo: ICajaRepository,
                 pago_repo: IPagoRepository):
        self.mesa_repo = mesa_repo
        self.comanda_repo = comanda_repo
        self.insumo_repo = insumo_repo
        self.caja_repo = caja_repo
        self.pago_repo = pago_repo

    def datos_mozo(self) -> dict:
        mesas = self.mesa_repo.listar_activas()
        comandas_activas = self.comanda_repo.contar_activas()
        alertas = self.insumo_repo.listar_criticos()
        ultimas_comandas = [
            c for c in self.comanda_repo.listar_activas()
            if c.estado in ['ABIERTA', 'EN_PREPARACION']
        ][:5]
        return {
            'mesas_libres': sum(1 for m in mesas if m.estado == 'LIBRE'),
            'mesas_ocupadas': sum(1 for m in mesas if m.estado == 'OCUPADA'),
            'comandas_activas': comandas_activas,
            'alertas_stock': len(alertas),
            'ultimas_comandas': ultimas_comandas,
            'alertas_detalle': alertas[:5],
        }

    def datos_cajero(self) -> dict:
        hoy = datetime.now(timezone.utc).date()
        pagos_hoy = self.pago_repo.listar_por_rango_fecha(
            hoy, hoy + timedelta(days=1)
        )
        total_ventas = sum(p.monto for p in pagos_hoy)
        caja_actual = self.caja_repo.obtener_abierta()
        return {
            'ventas_hoy': total_ventas,
            'caja_actual': caja_actual,
        }


class UsuarioService:
    """Gestión de usuarios del sistema."""

    def __init__(self, usuario_repo: IUsuarioRepository):
        self.repo = usuario_repo

    def obtener_por_id(self, user_id: int):
        user = self.repo.obtener_por_id(user_id)
        if not user:
            raise RecursoNoEncontrado('Usuario no encontrado')
        return user

    def listar_usuarios(self):
        return self.repo.listar()

    def crear(self, username: str, password: str,
              grupo_nombre: str = None, **extra):
        return self.repo.crear(
            username=username, password=password,
            grupo_nombre=grupo_nombre, **extra
        )

    def actualizar(self, user_id: int, solicitante_id: int, **campos):
        user = self.repo.obtener_por_id(user_id)
        if not user:
            raise RecursoNoEncontrado('Usuario no encontrado')

        is_active = campos.get('is_active', user.is_active)
        if not is_active and user_id == solicitante_id:
            raise ReglaNegocioViolada('No puedes desactivar tu propio usuario')

        for attr in ('username', 'first_name', 'last_name', 'email'):
            if attr in campos:
                setattr(user, attr, campos[attr])

        user.is_active = is_active

        password = campos.get('password')
        if password:
            user.password_hash = password

        rol = campos.get('rol')
        if rol == 'Admin':
            user.is_superuser = True
            user.is_staff = True
        else:
            user.is_superuser = False
            user.is_staff = False

        user = self.repo.actualizar(user)

        if rol is not None:
            self.repo.sincronizar_grupos(user_id, rol)

        return user

    def desactivar(self, user_id: int, solicitante_id: int):
        if user_id == solicitante_id:
            raise ReglaNegocioViolada('No puedes desactivarte a ti mismo')
        user = self.repo.obtener_por_id(user_id)
        if not user:
            raise RecursoNoEncontrado('Usuario no encontrado')
        user.is_active = False
        return self.repo.actualizar(user)

    def obtener_panel_destino(self, user_id: int) -> str:
        user = self.repo.obtener_por_id(user_id)
        if not user:
            return 'login'
        if 'Cocinero' in user.grupos and not user.is_superuser:
            return 'kds_panel'
        return 'dashboard'

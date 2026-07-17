class AppError(Exception):
    """Base de todas las excepciones de dominio."""

class ReglaNegocioViolada(AppError):
    pass

class TransicionEstadoInvalida(ReglaNegocioViolada):
    pass

class MesaConComandaActiva(ReglaNegocioViolada):
    pass

class CajaNoAbierta(ReglaNegocioViolada):
    pass

class ProductoSinStock(ReglaNegocioViolada):
    pass

class CapacidadExcedida(ReglaNegocioViolada):
    pass

class StockInsuficiente(ReglaNegocioViolada):
    pass

class PlatoNoDisponible(ReglaNegocioViolada):
    pass

class ComandaNoDisponible(ReglaNegocioViolada):
    pass

class MontoInvalido(ReglaNegocioViolada):
    pass

class ReferenciaInvalida(ReglaNegocioViolada):
    pass

class UnionInvalida(ReglaNegocioViolada):
    pass

class InsumoAgotado(ReglaNegocioViolada):
    pass

class UnidadConversionInvalida(ReglaNegocioViolada):
    pass

class MargenInvalidoError(ReglaNegocioViolada):
    pass

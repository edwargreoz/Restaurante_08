from typing import Protocol


class INotificadorPlano(Protocol):
    def notificar_refresh(self) -> None: ...


class INotificadorKDS(Protocol):
    def notificar_refresh(self) -> None: ...


class INotificadorComanda(Protocol):
    def notificar_comanda(self, comanda_id: int) -> None: ...

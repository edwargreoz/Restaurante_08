from typing import Optional, List
from django.contrib.auth.models import User, Group
from dominio.entidades.usuario import Usuario


class UsuarioRepository:

    def obtener_por_id(self, user_id: int) -> Optional[Usuario]:
        try:
            u = User.objects.prefetch_related('groups').get(id=user_id)
            return self._a_entidad(u)
        except User.DoesNotExist:
            return None

    def listar(self) -> List[Usuario]:
        return [
            self._a_entidad(u)
            for u in User.objects.prefetch_related('groups').order_by(
                '-is_active', 'username'
            )
        ]

    def crear(self, username: str, password: str,
              grupo_nombre: str = None, **extra) -> Usuario:
        user = User.objects.create_user(
            username=username, password=password, **extra
        )
        if grupo_nombre:
            grupo, _ = Group.objects.get_or_create(name=grupo_nombre)
            user.groups.add(grupo)
        return self._a_entidad(user)

    def actualizar(self, user: Usuario) -> Usuario:
        u = User.objects.get(id=user.id)
        u.username = user.username
        u.first_name = user.first_name
        u.last_name = user.last_name
        u.email = user.email
        u.is_active = user.is_active
        u.is_superuser = user.is_superuser
        u.is_staff = user.is_staff
        if user.password_hash:
            u.set_password(user.password_hash)
        u.save(update_fields=[
            'username', 'first_name', 'last_name', 'email',
            'is_active', 'is_superuser', 'is_staff',
        ])
        if user.password_hash:
            u.refresh_from_db()
        return self._a_entidad(u)

    def sincronizar_grupos(self, user_id: int, rol: str) -> None:
        u = User.objects.get(id=user_id)
        u.groups.clear()
        if rol and rol != 'Admin':
            grupo, _ = Group.objects.get_or_create(name=rol)
            u.groups.add(grupo)

    def obtener_usuario_orm(self, user_id: int):
        from django.contrib.auth.models import User
        return User.objects.get(id=user_id)

    def _a_entidad(self, u) -> Usuario:
        grupos = list(u.groups.values_list('name', flat=True))
        return Usuario(
            id=u.id, username=u.username,
            first_name=u.first_name, last_name=u.last_name,
            email=u.email, is_active=u.is_active,
            is_superuser=u.is_superuser, is_staff=u.is_staff,
            grupos=grupos,
        )

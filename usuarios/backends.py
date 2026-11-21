from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class PerfilModelBackend(ModelBackend):
    """Login por correo o username; exige usuario activo con institución activa."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        Usuario = get_user_model()
        user = (
            Usuario.objects.select_related('institucion')
            .filter(
                Q(username__iexact=username) | Q(email__iexact=username),
                institucion__isnull=False,
                institucion__activa=True,
                is_active=True,
            )
            .first()
        )

        if user is None:
            Usuario().set_password(password)  # mitiga ataques de temporización
            return None

        if user.check_password(password):
            return user
        return None
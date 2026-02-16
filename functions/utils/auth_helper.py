"""
Auth Helper - Utilidades para Firebase Authentication.

Funciones centralizadas para crear, eliminar y actualizar usuarios
en Firebase Authentication. DEBE SER USADA por todas las APIs que
gestionen usuarios de autenticación.
"""

import logging

from firebase_admin import auth

LOG = logging.getLogger(__name__)


def create_firebase_auth_user(email: str, password: str) -> str:
    """
    Crea un usuario en Firebase Authentication.

    Args:
        email: Email del usuario.
        password: Contraseña del usuario.

    Returns:
        UID del usuario creado en Firebase Auth.

    Raises:
        Exception: Si hay error al crear el usuario.
    """
    try:
        user = auth.create_user(
            email=email,
            password=password,
            email_verified=False,
        )
        LOG.info("Auth user creado: %s", user.uid)
        return user.uid
    except Exception as e:
        LOG.error("Error al crear auth user: %s", e, exc_info=True)
        raise


def delete_firebase_auth_user(uid: str) -> bool:
    """
    Elimina un usuario de Firebase Authentication.

    Usado en rollback cuando falla la creación. No lanza excepción si el
    usuario ya fue eliminado para no interrumpir el flujo de rollback.

    Args:
        uid: UID del usuario en Firebase Auth.

    Returns:
        True si se eliminó correctamente, False si hubo error.
    """
    try:
        auth.delete_user(uid)
        LOG.info("Auth user eliminado (rollback): %s", uid)
        return True
    except Exception as e:
        LOG.warning("Error al eliminar auth user (rollback): %s", e)
        return False


def update_firebase_auth_email(uid: str, new_email: str) -> bool:
    """
    Actualiza el email de un usuario en Firebase Auth.

    Args:
        uid: UID del usuario.
        new_email: Nuevo email.

    Returns:
        True si se actualizó correctamente.

    Raises:
        Exception: Si hay error al actualizar.
    """
    try:
        auth.update_user(uid, email=new_email)
        LOG.info("Auth email actualizado para uid: %s", uid)
        return True
    except Exception as e:
        LOG.error("Error al actualizar email auth: %s", e, exc_info=True)
        raise


def update_firebase_auth_password(uid: str, new_password: str) -> bool:
    """
    Actualiza la contraseña de un usuario en Firebase Auth.

    Args:
        uid: UID del usuario.
        new_password: Nueva contraseña.

    Returns:
        True si se actualizó correctamente.

    Raises:
        Exception: Si hay error al actualizar.
    """
    try:
        auth.update_user(uid, password=new_password)
        LOG.info("Auth password actualizado para uid: %s", uid)
        return True
    except Exception as e:
        LOG.error("Error al actualizar password auth: %s", e, exc_info=True)
        raise

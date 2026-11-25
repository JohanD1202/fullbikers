"""Limitación sencilla de intentos fallidos de inicio de sesión, en memoria.

Regla: 5 intentos fallidos para el mismo correo desde la misma IP en 15
minutos bloquean nuevos intentos hasta que el más antiguo salga de la ventana.
Un inicio de sesión exitoso borra el contador.

Limitaciones aceptadas para el alcance académico: el estado vive en la memoria
de cada proceso (con varios workers de Gunicorn cada uno lleva su cuenta) y se
pierde al reiniciar. No requiere tablas ni servicios externos.
"""
import threading
import time
from collections import deque

MAX_INTENTOS = 5
VENTANA_SEGUNDOS = 15 * 60


class LimitadorIntentos:
    def __init__(self, max_intentos=MAX_INTENTOS, ventana_segundos=VENTANA_SEGUNDOS, reloj=time.monotonic):
        self.max_intentos = max_intentos
        self.ventana = ventana_segundos
        self._reloj = reloj
        self._fallos = {}
        self._candado = threading.Lock()

    def _vigentes(self, clave, ahora):
        fallos = self._fallos.get(clave)
        if fallos is None:
            return None
        while fallos and ahora - fallos[0] >= self.ventana:
            fallos.popleft()
        if not fallos:
            del self._fallos[clave]
            return None
        return fallos

    def segundos_bloqueo(self, clave):
        """0 si se permite intentar; si no, segundos que faltan para poder hacerlo."""
        with self._candado:
            ahora = self._reloj()
            fallos = self._vigentes(clave, ahora)
            if fallos is None or len(fallos) < self.max_intentos:
                return 0
            return max(1, int(self.ventana - (ahora - fallos[0])) + 1)

    def registrar_fallo(self, clave):
        with self._candado:
            ahora = self._reloj()
            fallos = self._vigentes(clave, ahora)
            if fallos is None:
                fallos = self._fallos[clave] = deque()
            fallos.append(ahora)

    def reiniciar(self, clave):
        with self._candado:
            self._fallos.pop(clave, None)

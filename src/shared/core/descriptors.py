class classproperty:  # -> Clase decoradora para crear funciones que se comportan como propiedades de clase
    def __init__(self, fget):
        """
        fget: Es la función original que decoramos.
        Al escribir @classproperty sobre un método, ese método
        se pasa aquí como el argumento 'fget'.
        """
        self.fget = fget

    def __get__(self, _, owner):
        """
        get requiere una firma completa por protocolo (self, instance, owner)
        _ -> instance: es la instancia (será None si se accede desde la clase) | El objeto desde donde se llama (si existe).
        owner: La clase a la que pertenece el atributo.
        """
        return self.fget(owner)

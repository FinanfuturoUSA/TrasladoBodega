import re
from typing import cast


class StringUtils:
    @staticmethod
    def pluralizar_por_sep(cadena: str, sep: str, n: int | None = None) -> str:
        """
            Convierte a plural cada palabra en una cadena de texto estilo 'dunder_score'.

        Las reglas de pluralización que sigue son:
        1. Si la palabra termina en vocal (a, e, i, o, u), se le añade 's'.
        2. Si la palabra termina en 'z', se cambia la 'z' por 'ces'.
        3. Si la palabra termina en cualquier otra consonante, se le añade 'es'.
        """
        palabras = cadena.split(sep)
        palabras_en_plural = palabras[:n] if n else palabras
        palabras_en_singular = palabras[n:] if n else []

        for i in range(len(palabras_en_plural)):
            if not palabras_en_plural[i]:
                continue

            ultima_letra = palabras_en_plural[i][-1]

            if ultima_letra in "aeiou":
                palabras_en_plural[i] = palabras_en_plural[i] + "s"
            elif ultima_letra == "z":
                palabras_en_plural[i] = palabras_en_plural[i][:-1] + "ces"
            else:
                palabras_en_plural[i] = palabras_en_plural[i] + "es"

        return sep.join(palabras_en_plural + palabras_en_singular)

    @staticmethod
    def reemplazar_acentos_graves(cadena: str) -> str:
        tabla_traduccion = str.maketrans("àèìòùÀÈÌÒÙ", "áéíóúÁÉÍÓÚ")
        return cadena.translate(tabla_traduccion)

    @staticmethod
    def eliminar_acentos(cadena: str) -> str:
        tabla_traduccion = str.maketrans("àèìòùÀÈÌÒÙáéíóúÁÉÍÓÚ", "aeiouAEIOUaeiouAEIOU")
        return cadena.translate(tabla_traduccion)

    @staticmethod
    def contains_special_characters(cadena: str) -> bool:
        """
        Retorna True si contiene caracteres especiales como @, #, $, %, ^, *, (, ), _, +, =, ?, /, \\, |, {, }, [, ], ;, :, ', ", <, >, ., ,
        """
        pattern = r"[@#$%^*()_+=?/\\|{}\[\];:\'\"<>,.]"
        return bool(re.search(pattern, cadena))

    @staticmethod
    def clean_from_replace_dict(text: str, replace_dict: dict[str, str]) -> str:
        """
        Limpia el texto reemplazando caracteres según el diccionario proporcionado.

        Args:
            text: Texto a limpiar.
            replace_dict: Diccionario con los reemplazos {original: reemplazo}.

        Returns:
            Texto con los reemplazos aplicados.
        """
        for key, value in replace_dict.items():
            text = text.replace(key, value)
        return text

    @staticmethod
    def get_names_from_full_name(full_name: str) -> tuple[str, str, str, str]:
        """
        Extrae los nombres y apellidos de un nombre completo.

        Asume el formato: [nombres...] [primer_apellido] [segundo_apellido]

        Args:
            full_name: Nombre completo.

        Returns:
            Tupla con (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido).
        """
        names = full_name.split(" ")
        last_name = names[-2] if len(names) >= 2 else ""
        second_last_name = names[-1] if len(names) >= 1 else ""
        names = names[:-2] if len(names) > 2 else []
        first_name = ""
        second_name = ""
        if len(names) >= 2:
            first_name = names[0]
            second_name = " ".join(names[1:])
        else:
            first_name = " ".join(names)
        result = (first_name, second_name, last_name, second_last_name)
        result = tuple(word.capitalize() for word in result)
        return cast(tuple[str, str, str, str], result)

# Mallador Web

Backend usado en la aplicación del [Mallador](https://users.dcc.uchile.cl/~gaflores/mallador).

Para usar directamente el `UcampusEngine`, se puede hacer con el siguiente código:
```
from CatalogueEngine import UcampusEngine
ue = UcampusEngine()
catalogo = ue.query_all_subunidades({'semestre': 20192, 'unidad': 'fcfm'})
```
Donde `unidad` puede ser cualquiera de las presentes en el [Catálogo de Ucampus](https://ucampus.uchile.cl/m/fcfm_catalogo/).

También se incluye el script `dl_catalogo.py` usado por la [API](https://users.dcc.uchile.cl/~gaflores/mallador/catalogo.php?semestre=20192&unidad=fcfm) del Mallador. Este script espera que estén creadas las carpetas `catalogos` y `logs`, y el archivo `logs/dl_error.log`. La sintaxis de uso es:
```
python3 dl_catalogo.py [semestre] [unidad]
```
Donde `semestre` es un código de semestre válido (como `20192`), y `unidad` corresponde a las mismas definidas en el Catálogo.

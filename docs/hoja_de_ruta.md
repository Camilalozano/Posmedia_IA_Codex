# Desarrollo paso a paso

1. Implementado: consulta por referencia contractual, normalización de espacios/guiones/mayúsculas y mapeo inicial del formato. Pendiente: confirmar escala del avance de plazo y reglas de campos inferidos.
2. Implementado: conexión al CSV remoto de Oracle mediante `ORACLE_PAR_URL`, con carga manual de respaldo y mensajes seguros para renovar el PAR. Pendiente: supervisar vencimiento, definir un mecanismo estable sin PAR y recuperar el expediente.
3. Mejorar obligations.py con ejemplos anonimizados de distintos convenios, saltos de página y numeraciones.
4. Definir evidencia mínima por obligación, periodo aplicable y localización de soportes.
5. Incorporar propuestas automáticas de actividades y asociaciones respaldadas por fragmentos y páginas, con revisión humana.
6. Validar visualmente informes extensos y ampliar pruebas con el formato institucional aprobado.
7. Definir autenticación, conservación de archivos y condiciones de despliegue antes del uso operativo.

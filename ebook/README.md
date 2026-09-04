# El Faro de los Ahogados

Novela corta de terror y suspenso escrita por **Tito**, maquetada como
ebook profesional en PDF: portada ilustrada, prefacio, introducción,
índice con numeración automática, nueve capítulos a dos columnas con
ilustraciones, epílogo y nota sobre el autor. Cabeceras y pies de página
alternan el título de la obra y el capítulo en curso, con numeración
continua de páginas.

- **PDF final:** `output/El_Faro_de_los_Ahogados.pdf`
- **Ilustraciones** (generadas de forma procedural con PIL/numpy, estilo
  grabado/silueta): `assets/*.jpg`
- **Código fuente:**
  - `scripts/content.py` — texto completo de la novela.
  - `scripts/illustrations.py` — generación de la portada y las
    ilustraciones interiores.
  - `scripts/build_pdf.py` — maquetación editorial con ReportLab
    (portada a sangre completa, dos columnas, TOC automático,
    cabeceras/pies alternantes).

## Regenerar el PDF

```bash
pip install pillow reportlab numpy
cd ebook/scripts
python3 illustrations.py   # regenera las imágenes en ../assets
python3 build_pdf.py       # genera ../output/El_Faro_de_los_Ahogados.pdf
```

Este contenido no está relacionado con el resto del repositorio; vive en
su propia carpeta a pedido del usuario.

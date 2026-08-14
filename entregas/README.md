# Entregas de Trabajos Practicos

Esta carpeta concentra las entregas de los grupos. Cada grupo tiene una subcarpeta propia y debe mantener sus notebooks, conclusiones y materiales livianos dentro de ella.

## Grupos definidos

| Grupo | Carpeta | Integrantes |
|-------|---------|-------------|
| Grupo 1 | `grupo_01/` | Camila Ines Amado, Francisco Risculese, Agustin Macrina, Lucilam Pasquetta |
| Grupo 2 | `grupo_02/` | Jeremías Taran, Martin Gabriel Gomez, Jael Mataloni, Francisco Cisneros |

Estructura esperada:

```text
entregas/
├── grupo_01/
│   ├── README.md
│   ├── tp1/
│   │   ├── README.md
│   │   └── grupo_01_tp1.ipynb
│   ├── tp2/
│   │   ├── README.md
│   │   └── grupo_01_tp2.ipynb
│   ├── tp3/
│   │   ├── README.md
│   │   └── grupo_01_tp3.ipynb
│   └── tp4/
│       ├── README.md
│       └── link_presentacion.md
└── grupo_02/
    ├── README.md
    ├── tp1/
    │   ├── README.md
    │   └── grupo_02_tp1.ipynb
    ├── tp2/
    │   ├── README.md
    │   └── grupo_02_tp2.ipynb
    ├── tp3/
    │   ├── README.md
    │   └── grupo_02_tp3.ipynb
    └── tp4/
        ├── README.md
        └── link_presentacion.md
```

La carpeta `_template/` queda como referencia para futuras cohortes o grupos nuevos.

Reglas:

- No subir los CSV historicos completos (`datos_historicos_*.csv`) ni outputs pesados.
- Usar paths relativos desde la raiz del repo, por ejemplo `data/datos_historicos_2025.csv`.
- Cada TP debe tener un `README.md` breve con objetivo, notebook principal, supuestos, conclusion y pasos para reproducir.
- Si hay notebooks auxiliares, aclarar cual es el notebook principal de entrega.

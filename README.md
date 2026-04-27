# 🪿 Flappy Head - Game Controlled by Head Movement

Un juego tipo Flappy Bird controlado exclusivamente por el movimiento de tu cabeza usando Computer Vision.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Face%20Mesh-orange.svg)
![Pygame](https://img.shields.io/badge/Pygame-2.5-yellow.svg)

## 🎮 Demo

El juego usa tu cámara web para detectar el movimiento de tu cabeza en tiempo real usando **MediaPipe Face Mesh**.

## 🚀 Quick Start

### 1. Instalar dependencias

```bash
# Crear entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Ejecutar el juego

```bash
python src/main.py
```

### 3. Jugar!

1. **Permite acceso a la cámara** cuando el juego lo pida
2. **Calibración**: Mueve tu cabeza arriba y abajo durante 2 segundos
3. **Mueve tu cabeza hacia ARRIBA** para que el pato vuele
4. **Evita las tuberías** 🪿

## 🎯 Cómo funciona

```
Cámara Web → OpenCV → MediaPipe Face Mesh → Detección de nariz
                    ↓
              Comparación con calibración
                    ↓
              ¿Cabeza arriba? → ¡El pato vuela!
```

## 📋 Requisitos

- Python 3.8+
- Cámara web
- ~200MB de RAM
- GPU recomendada (funciona sin GPU)

## 🛠️ Tech Stack

| Tecnología | Uso |
|------------|-----|
| **MediaPipe** | Detección de landmarks faciales |
| **OpenCV** | Captura de video de cámara |
| **Pygame** | Renderizado del juego |
| **NumPy** | Procesamiento numérico |

## 🎮 Controles

| Acción | Control |
|--------|---------|
| Volar | Mueve cabeza ↑ ARRIBA |
| Iniciar | ESPACIO |
| Reiniciar | ESPACIO (después de Game Over) |
| Salir | ESC |

## 📁 Estructura del Proyecto

```
head-game/
├── src/
│   └── main.py          # Juego principal
├── requirements.txt     # Dependencias Python
├── README.md           # Este archivo
└── high_score.txt     # Puntuación más alta (generado automáticamente)
```

## 🔧 Troubleshooting

### La cámara no funciona
- Verifica que otra aplicación no esté usando la cámara
- Prueba con `cv2.VideoCapture(1)` si tienes varias cámaras

### Detección de cara imprecisa
- Asegúrate de tener buena iluminación
- La cara debe estar bien visible para la cámara

### Lag excesivo
- Cierra otras aplicaciones que usen cámara
- Reduce la resolución de captura

## 📝 Licencia

MIT - Libre para uso educativo y personal.

## 👤 Autor

Jonatan Hidalgo

---

**¡Diviértete volando con tu cabeza!** 🪿🚀

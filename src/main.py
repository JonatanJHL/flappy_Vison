import pygame
import cv2
import numpy as np
import random
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ─── Inicializar Pygame ───────────────────────────────────────────────────────
pygame.init()

# ─── Configuración de pantalla ────────────────────────────────────────────────
SCREEN_WIDTH  = 400
SCREEN_HEIGHT = 600
SPLIT_WIDTH   = 820   # Ancho para modo 2 jugadores (con margen)
FPS           = 60

# ─── Colores ──────────────────────────────────────────────────────────────────
SKY_BLUE   = (135, 206, 235)
SKY_DUSK   = (255, 180, 120)
GREEN      = (34, 139, 34)
DARK_GREEN = (0, 100, 0)
WHITE      = (255, 255, 255)
BLACK      = (0, 0, 0)
ORANGE     = (255, 165, 0)
RED        = (220, 50, 50)
GOLD       = (255, 215, 0)
CYAN       = (80, 200, 255)
PURPLE     = (160, 80, 220)

# ─── Configuración del juego ──────────────────────────────────────────────────
GRAVITY         = 0.45
FLAP_STRENGTH   = -8
PIPE_GAP_START  = 160   # gap inicial, se reduce con el score
PIPE_SPEED_BASE = 3
PIPE_SPAWN_BASE = 95


# ══════════════════════════════════════════════════════════════════════════════
#  CLASE BIRD
# ══════════════════════════════════════════════════════════════════════════════
class Bird:
    STATE_ALIVE  = "alive"
    STATE_HURT   = "hurt"
    STATE_SHIELD = "shield"
    STATE_DEAD   = "dead"

    def __init__(self, x, y, color_scheme=1):
        self.x = x
        self.y = float(y)
        self.velocity   = 0.0
        self.lives      = 3
        self.state      = self.STATE_ALIVE
        self.hurt_timer  = 0
        self.shield_timer = 0
        self.color_scheme = color_scheme  # 1 = amarillo (J1), 2 = azul (J2)

        # Colores según esquema
        if color_scheme == 1:
            self.body_color = (255, 220, 0)    # Amarillo
            self.wing_color = (230, 200, 0)
            self.dark_color = (200, 175, 0)
        else:
            self.body_color = (70, 130, 255)   # Azul
            self.wing_color = (50, 110, 230)
            self.dark_color = (40, 90, 200)

        # Animación de alas
        self.wing_angle = 0.0
        self.wing_dir   = 1
        self.flap_timer = 0

        # Partículas de muerte
        self.particles = []

    # ── Control ──────────────────────────────────────────────────────────────
    def flap(self, strength=1):
        if self.state == self.STATE_DEAD:
            return
        if strength == 0:  # Fuerte
            self.velocity = -10
        elif strength == 1:  # Bajo
            self.velocity = -6
        else:  # Normal
            self.velocity = FLAP_STRENGTH
        self.flap_timer = 14

    def activate_shield(self, duration=200):
        if self.state == self.STATE_DEAD:
            return
        self.state        = self.STATE_SHIELD
        self.shield_timer = duration

    def take_hit(self):
        """Devuelve True si el pato murió."""
        if self.state in (self.STATE_HURT, self.STATE_DEAD):
            return False
        if self.state == self.STATE_SHIELD:
            self.state        = self.STATE_ALIVE
            self.shield_timer = 0
            return False
        self.lives -= 1
        if self.lives <= 0:
            self.state = self.STATE_DEAD
            self._spawn_particles()
            return True
        self.state      = self.STATE_HURT
        self.hurt_timer = 90
        return False

    # ── Update ────────────────────────────────────────────────────────────────
    def update(self):
        if self.state == self.STATE_DEAD:
            self._update_particles()
            return

        # Física
        self.velocity += GRAVITY
        self.velocity  = min(self.velocity, 10)
        self.y        += self.velocity

        # Alas
        wing_speed = 15 if self.flap_timer > 0 else 5
        self.wing_angle += wing_speed * self.wing_dir
        if self.wing_angle > 38 or self.wing_angle < -38:
            self.wing_dir *= -1
        if self.flap_timer > 0:
            self.flap_timer -= 1

        # Timers de estado
        if self.hurt_timer > 0:
            self.hurt_timer -= 1
            if self.hurt_timer == 0:
                self.state = self.STATE_ALIVE
        if self.shield_timer > 0:
            self.shield_timer -= 1
            if self.shield_timer == 0:
                self.state = self.STATE_ALIVE

    def _spawn_particles(self):
        if self.color_scheme == 1:
            colors = [(255,220,0),(255,165,0),(255,255,255),(255,100,100)]
        else:
            colors = [(70,130,255),(100,150,255),(255,255,255),(100,100,255)]
        for _ in range(26):
            self.particles.append({
                'x': self.x + 20, 'y': self.y + 15,
                'vx': random.uniform(-5, 5),
                'vy': random.uniform(-7, 0),
                'life': random.randint(22, 48),
                'max_life': 48,
                'color': random.choice(colors),
                'size': random.uniform(3, 8),
            })

    def _update_particles(self):
        for p in self.particles:
            p['x']  += p['vx']
            p['y']  += p['vy']
            p['vy'] += 0.35
            p['life'] -= 1
        self.particles = [p for p in self.particles if p['life'] > 0]

    # ── Colisión ──────────────────────────────────────────────────────────────
    def get_rect(self):
        return pygame.Rect(int(self.x) + 4, int(self.y) + 4, 30, 22)

    # ── Dibujo ────────────────────────────────────────────────────────────────
    def draw(self, screen):
        if self.state == self.STATE_DEAD:
            self._draw_particles(screen)
            return

        # Parpadeo cuando está dañado
        if self.state == self.STATE_HURT:
            if (self.hurt_timer // 6) % 2 == 0:
                return

        surf = pygame.Surface((52, 44), pygame.SRCALPHA)

        # Sombra
        pygame.draw.ellipse(surf, (0, 0, 0, 35), (7, 36, 34, 7))

        # Ala trasera (animada)
        wy = 20 + math.sin(math.radians(self.wing_angle)) * 7
        pygame.draw.ellipse(surf, self.dark_color, (9, int(wy), 20, 9))

        # Cuerpo
        pygame.draw.ellipse(surf, self.body_color, (5, 12, 34, 22))

        # Brillo en cuerpo
        if self.color_scheme == 1:
            highlight = (255, 255, 180, 120)  # Amarillo brillante
        else:
            highlight = (180, 220, 255, 120)  # Azul brillante
        pygame.draw.ellipse(surf, highlight, (8, 13, 14, 8))

        # Ala delantera (animada)
        pygame.draw.ellipse(surf, self.wing_color, (9, int(wy - 2), 22, 10))

        # Ojo blanco
        pygame.draw.circle(surf, WHITE, (36, 17), 5)
        # Pupila
        pygame.draw.circle(surf, (20, 20, 40), (37, 17), 3)
        # Brillo ojo
        pygame.draw.circle(surf, WHITE, (38, 15), 1)

        # Pico (naranja para ambos)
        pygame.draw.polygon(surf, (255, 130, 0), [(40, 18), (50, 21), (40, 24)])
        pygame.draw.polygon(surf, (220, 100, 0), [(40, 21), (50, 21), (40, 24)])

        # Escudo pulsante (diferente color según jugador)
        if self.state == self.STATE_SHIELD:
            t = pygame.time.get_ticks()
            alpha = int(110 + math.sin(t / 90) * 60)
            radius = int(28 + math.sin(t / 120) * 3)
            shield_color = (0, 200, 100) if self.color_scheme == 1 else (100, 100, 255)
            shield_surf = pygame.Surface((52, 44), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (*shield_color, alpha), (26, 22), radius, 3)
            surf.blit(shield_surf, (0, 0))

        # Rotar según velocidad
        rotation = min(max(self.velocity * 3, -30), 50)
        rotated  = pygame.transform.rotate(surf, -rotation)
        screen.blit(rotated, (int(self.x) - 5, int(self.y) - 5))

    def _draw_particles(self, screen):
        for p in self.particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            s     = pygame.Surface((int(p['size'] * 2 + 1),) * 2, pygame.SRCALPHA)
            pygame.draw.circle(
                s, (*p['color'], alpha),
                (int(p['size']),) * 2, int(p['size'])
            )
            screen.blit(s, (int(p['x']), int(p['y'])))


# ══════════════════════════════════════════════════════════════════════════════
#  CLASE POWER-UP
# ══════════════════════════════════════════════════════════════════════════════
class PowerUp:
    TYPE_SHIELD  = "shield"
    TYPE_SLOW    = "slow"
    TYPE_LIFE    = "life"

    ICONS = {
        TYPE_SHIELD: "🛡",
        TYPE_SLOW:   "⏱",
        TYPE_LIFE:   "❤",
    }
    COLORS = {
        TYPE_SHIELD: CYAN,
        TYPE_SLOW:   PURPLE,
        TYPE_LIFE:   RED,
    }

    def __init__(self, x, y, kind):
        self.x    = float(x)
        self.y    = float(y)
        self.kind = kind
        self.collected = False
        self.t    = 0

    def update(self, pipe_speed):
        self.x -= pipe_speed
        self.t += 1

    def get_rect(self):
        return pygame.Rect(int(self.x) - 14, int(self.y) - 14, 28, 28)

    def draw(self, screen, font):
        if self.collected:
            return
        bob = math.sin(self.t / 20) * 4
        color = self.COLORS[self.kind]

        # Fondo circular con brillo pulsante
        alpha = int(160 + math.sin(self.t / 15) * 40)
        s = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (17, 17), 16)
        pygame.draw.circle(s, (255, 255, 255, 80), (17, 17), 16, 2)
        screen.blit(s, (int(self.x) - 17, int(self.y + bob) - 17))

        # Icono
        icon = font.render(self.ICONS[self.kind], True, WHITE)
        screen.blit(icon, (int(self.x) - icon.get_width() // 2,
                           int(self.y + bob) - icon.get_height() // 2))


# ══════════════════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL GAME
# ══════════════════════════════════════════════════════════════════════════════
class Game:

    MODE_INFINITE  = "infinite"
    MODE_MISSION   = "mission"
    MODE_SPLIT     = "split"    # 2 jugadores pantalla dividida

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Flappy Hand – ¡Controla con tu mano!")
        self.clock    = pygame.time.Clock()
        self.font     = pygame.font.Font(None, 34)
        self.big_font = pygame.font.Font(None, 68)
        self.sm_font  = pygame.font.Font(None, 26)

        # Estado global
        self.running      = True
        self.scene        = "menu"   # menu | instructions | game | gameover | pause
        self.mode         = self.MODE_INFINITE
        self.score        = 0
        self.high_score   = self._load_high_score()
        self.mission_goal = 10       # pipes a pasar en modo misión

        # Variables de juego
        self.bird        = None
        self.bird2       = None      # Segundo jugador (multijugador)
        self.pipes       = []
        self.powerups     = []
        self.frame_count  = 0
        self.slow_timer  = 0         # power-up cámara lenta activo

        # Nubes animadas
        self.clouds = [
            {'x': random.randint(0, SCREEN_WIDTH), 'y': random.randint(40, 160),
             'speed': random.uniform(0.3, 0.7), 'size': random.randint(22, 38)}
            for _ in range(6)
        ]

        # Parallax capas (offset)
        self.bg_offset = 0.0

        # Cámara
        self.cap = cv2.VideoCapture(0)

        # MediaPipe Hands - detecta hasta 2 manos
        base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.hand_detector = vision.HandLandmarker.create_from_options(options)
        
        # Control de manos (2 jugadores)
        self.hand_was_open = [True, True]
        self.gesture_cooldown = [0, 0]
        self.current_hands = []  # Manos detectadas en el frame actual

        # Assets
        self._build_ground()

        # Calibración
        self._calibrate()

    # ── Assets ────────────────────────────────────────────────────────────────
    def _build_ground(self):
        self.ground = pygame.Surface((SCREEN_WIDTH, 80))
        self.ground.fill(GREEN)
        for i in range(0, SCREEN_WIDTH, 18):
            pygame.draw.polygon(
                self.ground, DARK_GREEN,
                [(i, 0), (i + 9, 22), (i + 18, 0)]
            )

    # ── Calibración ───────────────────────────────────────────────────────────
    def _calibrate(self):
        samples = []
        while len(samples) < 30:
            ret, frame = self.cap.read()
            if not ret:
                continue
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            res   = self.hand_detector.detect(img)
            if res.hand_landmarks:
                samples.append(len(res.hand_landmarks))

            # Pantalla de calibración
            self.screen.fill(SKY_BLUE)
            prog = len(samples) / 30
            pygame.draw.rect(self.screen, (255,255,255,180),
                             (50, SCREEN_HEIGHT//2-22, 300, 44), border_radius=8)
            pygame.draw.rect(self.screen, GREEN,
                             (50, SCREEN_HEIGHT//2-22, int(300*prog), 44), border_radius=8)
            
            if self.mode == self.MODE_SPLIT:
                self._blit_text("¡2 JUGADORES! Muestra 2 manos", self.font,
                                WHITE, SCREEN_HEIGHT//2 - 80)
            else:
                self._blit_text("Muestra tu mano frente a la cámara", self.font,
                                WHITE, SCREEN_HEIGHT//2 - 80)
            self._blit_text(f"Calibrando... {int(prog*100)}%", self.sm_font,
                            WHITE, SCREEN_HEIGHT//2 + 42)

            # Mini-cámara y mostrar detección de mano(s)
            small = cv2.resize(frame, (110, 82))
            small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            
            # Dibujar indicadores para cada mano
            if res.hand_landmarks:
                h_s, w_s = small.shape[:2]
                colors = [(0, 255, 0), (255, 0, 255)]  # Verde y magenta para 2 manos
                for i, hand_landmarks in enumerate(res.hand_landmarks):
                    color = colors[i % 2]
                    for lm in hand_landmarks:
                        x = int(lm.x * w_s)
                        y = int(lm.y * h_s)
                        cv2.circle(small, (x, y), 1, color, -1)
                cv2.putText(small, f"{len(res.hand_landmarks)} mano(s)", (5, 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            cam_surf = pygame.surfarray.make_surface(small.swapaxes(0, 1))
            pygame.draw.rect(self.screen, WHITE,
                             (SCREEN_WIDTH-124, 8, 114, 86), border_radius=6)
            self.screen.blit(cam_surf, (SCREEN_WIDTH-121, 11))
            cv2.imshow("Control de Mano - Flappy Hand", frame)
            cv2.waitKey(1)
            pygame.display.flip()

        self.calibrated = True
        if self.mode == self.MODE_SPLIT:
            print("[Calibración] ¡2 jugadores listos!")
        else:
            print("[Calibración] ¡Listo! Usa tu mano para controlar.")

    # ── Detectar estado de manos (para 1 o 2 jugadores) ───────────────────────
    # Retorna: lista de diccionarios con {state, x_position, hand_index}
    # Usa caché para reducir carga de procesamiento
    def _get_hands_state(self):
        # Solo procesar cada 2 frames para reducir carga
        if not hasattr(self, '_frame_counter'):
            self._frame_counter = 0
        self._frame_counter += 1
        
        if self._frame_counter % 2 != 0 and hasattr(self, '_cached_hands'):
            # Mostrar cámara pero usar datos en caché
            ret, frame = self.cap.read()
            if ret:
                cv2.imshow("Control de Mano - Flappy Hand", frame)
                cv2.waitKey(1)
            return self._cached_hands
        
        ret, frame = self.cap.read()
        if not ret:
            return []
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = self.hand_detector.detect(img)
        
        h, w = frame.shape[:2]
        hands_data = []  # [{state, x_pos}]
        
        # Fondo semi-transparente para texto
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 80), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.3, frame, 0.7, 0)
        
        if not res.hand_landmarks:
            cv2.putText(frame, "MANOS NO DETECTADAS - Muestra tus manos!", (10, 40),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow("Control de Mano - Flappy Hand", frame)
            cv2.waitKey(1)
            return []
        
        # Ordenar manos por posición X (izquierda primero)
        hands_sorted = sorted(enumerate(res.hand_landmarks), 
                             key=lambda x: x[1][0].x)
        
        for idx, (original_idx, hand_landmarks) in enumerate(hands_sorted):
            wrist_x = hand_landmarks[0].x
            wrist_x_px = int(wrist_x * w)
            
            # Color según posición: Verde = J1 (izquierda), Azul = J2 (derecha)
            if wrist_x < 0.5:
                player_color = (0, 255, 0)  # Verde - Jugador 1
                player_name = "JUGADOR 1"
                player_short = "J1"
            else:
                player_color = (255, 100, 50)  # Naranja/azul - Jugador 2
                player_name = "JUGADOR 2"
                player_short = "J2"
            
            # Calcular bounding box de la mano
            xs = [int(lm.x * w) for lm in hand_landmarks]
            ys = [int(lm.y * h) for lm in hand_landmarks]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Dibujar rectángulo grande alrededor de la mano
            padding = 30
            cv2.rectangle(frame, 
                         (max(0, min_x - padding), max(0, min_y - padding)),
                         (min(w, max_x + padding), min(h, max_y + padding)),
                         player_color, 3)
            
            # Dibujar etiqueta del jugador
            cv2.putText(frame, player_name, 
                       (max(5, min_x - padding), max(25, min_y - padding - 5)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, player_color, 2)
            
            # Dibujar hand landmarks con colores
            for landmark in hand_landmarks:
                x, y = int(landmark.x * w), int(landmark.y * h)
                cv2.circle(frame, (x, y), 3, player_color, -1)
            
            # Detectar estado de mano (3 niveles) con algoritmo mejorado
            # Comparar distancia entre punta y base de cada dedo
            fingertips = [8, 12, 16, 20]  # Índice, medio, anular, meñique
            fingerbases = [5, 9, 13, 17]
            
            fingers_extended = 0
            finger_distances = []
            
            for tip, base in zip(fingertips, fingerbases):
                tip_x, tip_y = hand_landmarks[tip].x * w, hand_landmarks[tip].y * h
                base_x, base_y = hand_landmarks[base].x * w, hand_landmarks[base].y * h
                
                # Calcular distancia euclidiana
                dist = ((tip_x - base_x) ** 2 + (tip_y - base_y) ** 2) ** 0.5
                finger_distances.append(dist)
                
                # Dedo extendido si la distancia es mayor a un umbral
                # Ajustamos según el tamaño de la mano detectado
                avg_hand_size = max(xs) - min(xs)
                threshold = avg_hand_size * 0.3  # 30% del tamaño de la mano
                
                if dist > threshold:
                    fingers_extended += 1
            
            # Promedio de distancias para determinar estado
            avg_dist = sum(finger_distances) / len(finger_distances)
            max_dist = max(finger_distances) if finger_distances else 0
            
            # 3 estados:
            # 0 = PUÑO (0-1 dedos extendidos)
            # 1 = SEMI (2 dedos extendidos o distancia media)
            # 2 = ABIERTO (3-4 dedos extendidos)
            
            if fingers_extended <= 1:
                state = 0  # PUÑO
            elif fingers_extended == 2:
                state = 1  # SEMI
            else:
                state = 2  # ABIERTO
            
            hands_data.append({'state': state, 'x_pos': wrist_x, 'fingers': fingers_extended})
            
            # Dibujar estado en la parte superior
            text_y = 30 + idx * 40
            
            # Estado con nombre descriptivo y color
            if state == 0:
                state_text = "PUÑO - SALTA!"
                state_color = (0, 0, 255)  # Rojo
            elif state == 1:
                state_text = "SEMI - suave"
                state_color = (0, 255, 255)  # Amarillo
            else:
                state_text = "ABIERTO - baja"
                state_color = (0, 255, 0)  # Verde
            
            cv2.putText(frame, f"{player_short}: {state_text} ({fingers_extended}/4 dedos)", 
                       (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, state_color, 2)
            
            # Dibujar indicador visual del estado
            bar_x, bar_y = w - 50, text_y - 15
            bar_h = 25
            if state == 0:
                cv2.putText(frame, "PUÑO", (bar_x, bar_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, state_color, 1)
            elif state == 1:
                cv2.putText(frame, "SEMI", (bar_x, bar_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, state_color, 1)
            else:
                cv2.putText(frame, "ABIERTO", (bar_x - 15, bar_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, state_color, 1)
        
        # Instrucciones en la parte inferior
        cv2.rectangle(frame, (0, h - 50), (w, h), (0, 0, 0), -1)
        cv2.putText(frame, "[ABIERTO]=baja  [SEMI]=salto suave  [PUÑO]=salto fuerte", 
                   (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        
        cv2.imshow("Control de Mano - Flappy Hand", frame)
        cv2.waitKey(1)
        
        # Guardar en caché
        self._cached_hands = hands_data
        return hands_data

    # ── Helpers de texto ──────────────────────────────────────────────────────
    def _blit_text(self, text, font, color, cy, cx=None):
        surf = font.render(text, True, color)
        x    = (SCREEN_WIDTH - surf.get_width()) // 2 if cx is None else cx
        self.screen.blit(surf, (x, cy))
    
    def _blit_text_surf(self, surf, text, font, color, cy, cx=None):
        text_surf = font.render(text, True, color)
        x    = (surf.get_width() - text_surf.get_width()) // 2 if cx is None else cx
        surf.blit(text_surf, (x, cy))

    # ── Dificultad dinámica ───────────────────────────────────────────────────
    def _pipe_speed(self):
        extra = min(self.score // 8, 4)
        if self.slow_timer > 0:
            return max(1.5, (PIPE_SPEED_BASE + extra) * 0.55)
        return PIPE_SPEED_BASE + extra

    def _pipe_gap(self):
        return max(110, PIPE_GAP_START - self.score * 2)

    def _spawn_rate(self):
        return max(60, PIPE_SPAWN_BASE - self.score)

    # ── Reset de partida ──────────────────────────────────────────────────────
    def _reset(self):
        self.bird        = Bird(55, SCREEN_HEIGHT // 2, color_scheme=1)
        self.bird2       = None
        if self.mode == self.MODE_SPLIT:
            self.bird2   = Bird(55, SCREEN_HEIGHT // 2, color_scheme=2)
            self.bird2.lives = 3
            self.pipes2  = []  # Pipes del jugador 2
            self.powerups2 = []
        self.pipes       = []
        self.powerups    = []
        self.frame_count = 0
        self.score       = 0
        self.score2      = 0  # Score del jugador 2
        self.slow_timer  = 0
        self.hand_was_open = [2, 2]  # Estado abierto por defecto
        self.gesture_cooldown = [0, 0]
        self.hand_assignment = [None, None]  # Qué mano detecta para cada jugador
        self._frame_counter = 0  # Reset counter
        self._cached_hands = []  # Limpiar caché
        self.scene       = "game"

    # ══════════════════════════════════════════════════════════════════════════
    #  EVENTOS
    # ══════════════════════════════════════════════════════════════════════════
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.scene == "game":
                        self.scene = "pause"
                    elif self.scene == "pause":
                        self.scene = "game"
                    elif self.scene == "instructions":
                        self.scene = "menu"
                    else:
                        self.running = False

                elif event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_RETURN):
                    if self.scene == "menu":
                        self.scene = "instructions"  # Ir a instrucciones
                    elif self.scene == "instructions":
                        self._reset()  # Empezar juego
                        # Redimensionar para modo split
                        if self.mode == self.MODE_SPLIT:
                            pygame.display.set_mode((SCREEN_WIDTH * 2, SCREEN_HEIGHT))
                        else:
                            pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    elif self.scene == "gameover":
                        self.scene = "menu"
                        # Volver al tamaño normal
                        pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    elif self.scene == "pause":
                        self.scene = "game"
                    elif self.scene == "game" and self.bird:
                        self.bird.flap()

                # Cambiar modo en menú
                elif event.key == pygame.K_m and self.scene == "menu":
                    if self.mode == self.MODE_INFINITE:
                        self.mode = self.MODE_MISSION
                    elif self.mode == self.MODE_MISSION:
                        self.mode = self.MODE_SPLIT
                    else:
                        self.mode = self.MODE_INFINITE

    # ══════════════════════════════════════════════════════════════════════════
    #  UPDATE
    # ══════════════════════════════════════════════════════════════════════════
    def update(self):
        if self.scene not in ("game", "instructions"):
            return
        
        # En instrucciones, solo mostrar la cámara
        if self.scene == "instructions":
            ret, frame = self.cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = self.hand_detector.detect(img)
                
                h, w = frame.shape[:2]
                if res.hand_landmarks:
                    for hand_landmarks in res.hand_landmarks:
                        for lm in hand_landmarks:
                            x = int(lm.x * w)
                            y = int(lm.y * h)
                            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)
                    cv2.putText(frame, f"{len(res.hand_landmarks)} mano(s) detectada(s)", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    cv2.putText(frame, "Muestra tu mano(s)", 
                               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.imshow("Control de Mano - Flappy Hand", frame)
                cv2.waitKey(1)
            return

        speed = self._pipe_speed()
        gap   = self._pipe_gap()

        # Detectar manos con posición
        hands_data = self._get_hands_state()
        
        # Cooldowns
        for i in range(len(self.gesture_cooldown)):
            if self.gesture_cooldown[i] > 0:
                self.gesture_cooldown[i] -= 1

        # Asignar manos a jugadores por posición X
        # Mano izquierda = Jugador 1, Mano derecha = Jugador 2
        player_states = [2, 2]  # Estados de cada jugador (2 = abierto)
        
        for hand in hands_data:
            if hand['x_pos'] < 0.5:  # Mano izquierda
                player_states[0] = hand['state']
            else:  # Mano derecha
                if self.mode == self.MODE_SPLIT:
                    player_states[1] = hand['state']

        # Control jugador 1
        if self.gesture_cooldown[0] == 0:
            prev = self.hand_was_open[0] if self.hand_was_open else 2
            if player_states[0] == 0 and prev != 0:
                self.bird.flap(0)
                self.gesture_cooldown[0] = 12
            elif player_states[0] == 1 and prev == 2:
                self.bird.flap(1)
                self.gesture_cooldown[0] = 15

        # Control jugador 2 (modo split)
        if self.mode == self.MODE_SPLIT and self.gesture_cooldown[1] == 0:
            prev = self.hand_was_open[1] if len(self.hand_was_open) > 1 else 2
            if player_states[1] == 0 and prev != 0:
                self.bird2.flap(0)
                self.gesture_cooldown[1] = 12
            elif player_states[1] == 1 and prev == 2:
                self.bird2.flap(1)
                self.gesture_cooldown[1] = 15

        # Actualizar estados de manos
        self.hand_was_open = player_states.copy()

        # Birds
        self.bird.update()
        if self.mode == self.MODE_SPLIT and self.bird2:
            self.bird2.update()

        # Límites de pantalla jugador 1
        if self.bird.y >= SCREEN_HEIGHT - 80:
            self.bird.y = float(SCREEN_HEIGHT - 80)
            if self.bird.state != Bird.STATE_DEAD:
                if self.bird.take_hit():
                    if self.mode == self.MODE_SPLIT:
                        if self.bird2 and self.bird2.state == Bird.STATE_DEAD:
                            self._end_game()
                    else:
                        self._end_game()
                    return

        if self.bird.y < -10:
            self.bird.y = -10.0
            self.bird.velocity = 0

        # Límites de pantalla jugador 2
        if self.mode == self.MODE_SPLIT and self.bird2:
            if self.bird2.y >= SCREEN_HEIGHT - 80:
                self.bird2.y = float(SCREEN_HEIGHT - 80)
                if self.bird2.state != Bird.STATE_DEAD:
                    if self.bird2.take_hit():
                        if self.bird.state == Bird.STATE_DEAD:
                            self._end_game()
                        return
            if self.bird2.y < -10:
                self.bird2.y = -10.0
                self.bird2.velocity = 0

        # Slow timer
        if self.slow_timer > 0:
            self.slow_timer -= 1

        # Spawn de pipes
        self.frame_count += 1
        if self.frame_count % self._spawn_rate() == 0:
            self._spawn_pipe(gap)
            if self.mode == self.MODE_SPLIT:
                self._spawn_pipe(gap, player=2)  # Pipe diferente para J2

        # Mover pipes y colisiones jugador 1
        for pipe in self.pipes:
            pipe['x'] -= speed

            if self.bird.state not in (Bird.STATE_HURT, Bird.STATE_DEAD):
                bird_rect = self.bird.get_rect()
                top_r = pygame.Rect(int(pipe['x']), 0, 52, pipe['gap_y'])
                bot_r = pygame.Rect(int(pipe['x']), pipe['gap_y'] + pipe['gap'],
                                    52, SCREEN_HEIGHT)
                if bird_rect.colliderect(top_r) or bird_rect.colliderect(bot_r):
                    if self.bird.take_hit():
                        if self.mode != self.MODE_SPLIT or (self.bird2 and self.bird2.state == Bird.STATE_DEAD):
                            self._end_game()
                        return

            if not pipe['passed'] and pipe['x'] + 52 < self.bird.x:
                pipe['passed'] = True
                self.score += 1
                if random.random() < 0.20:
                    self._spawn_powerup(pipe, self.powerups)
                if self.mode == self.MODE_MISSION and self.score >= self.mission_goal:
                    self._end_game(victory=True)
                    return

        self.pipes = [p for p in self.pipes if p['x'] > -70]

        # Pipes y colisiones jugador 2
        if self.mode == self.MODE_SPLIT:
            for pipe in self.pipes2:
                pipe['x'] -= speed

                if self.bird2.state not in (Bird.STATE_HURT, Bird.STATE_DEAD):
                    bird_rect2 = self.bird2.get_rect()
                    top_r2 = pygame.Rect(int(pipe['x']), 0, 52, pipe['gap_y'])
                    bot_r2 = pygame.Rect(int(pipe['x']), pipe['gap_y'] + pipe['gap'],
                                        52, SCREEN_HEIGHT)
                    if bird_rect2.colliderect(top_r2) or bird_rect2.colliderect(bot_r2):
                        if self.bird2.take_hit():
                            if self.bird.state == Bird.STATE_DEAD:
                                self._end_game()
                            return

                if not pipe['passed'] and pipe['x'] + 52 < self.bird2.x:
                    pipe['passed'] = True
                    self.score2 += 1

            self.pipes2 = [p for p in self.pipes2 if p['x'] > -70]

        # Power-ups
        for pu in self.powerups:
            pu.update(speed)
            if not pu.collected and pu.get_rect().colliderect(self.bird.get_rect()):
                pu.collected = True
                self._apply_powerup(pu.kind)
            if self.mode == self.MODE_SPLIT and self.bird2:
                if not pu.collected and pu.get_rect().colliderect(self.bird2.get_rect()):
                    pu.collected = True
                    self._apply_powerup(pu.kind)

        self.powerups = [p for p in self.powerups if not p.collected and p.x > -50]

        # Nubes
        for c in self.clouds:
            c['x'] -= c['speed']
            if c['x'] < -80:
                c['x'] = SCREEN_WIDTH + 40
                c['y'] = random.randint(40, 160)

        self.bg_offset = (self.bg_offset + 0.5) % SCREEN_WIDTH

    def _check_game_over(self):
        if self.mode == self.MODE_SPLIT:
            p1_dead = self.bird.state == Bird.STATE_DEAD
            p2_dead = self.bird2 and self.bird2.state == Bird.STATE_DEAD
            if p1_dead and p2_dead:
                self._end_game()
        else:
            self._end_game()

    def _spawn_pipe(self, gap, player=1):
        gy = random.randint(90, SCREEN_HEIGHT - 180)
        pipe = {'x': float(SCREEN_WIDTH), 'gap_y': gy, 'gap': gap, 'passed': False}
        if player == 1:
            self.pipes.append(pipe)
        else:
            self.pipes2.append(pipe)

    def _spawn_powerup(self, pipe, powerup_list):
        gy   = pipe['gap_y']
        gap  = pipe['gap']
        cy   = gy + gap // 2
        kind = random.choice([PowerUp.TYPE_SHIELD,
                               PowerUp.TYPE_SLOW,
                               PowerUp.TYPE_LIFE])
        powerup_list.append(PowerUp(SCREEN_WIDTH + 80, cy, kind))

    def _apply_powerup(self, kind):
        if kind == PowerUp.TYPE_SHIELD:
            self.bird.activate_shield(220)
            if self.mode == self.MODE_SPLIT and self.bird2:
                self.bird2.activate_shield(220)
        elif kind == PowerUp.TYPE_SLOW:
            self.slow_timer = 240
        elif kind == PowerUp.TYPE_LIFE:
            self.bird.lives = min(self.bird.lives + 1, 5)
            if self.mode == self.MODE_SPLIT and self.bird2:
                self.bird2.lives = min(self.bird2.lives + 1, 5)

    def _end_game(self, victory=False):
        if self.score > self.high_score:
            self.high_score = self.score
            self._save_high_score()
        self.scene   = "gameover"
        self.victory = victory

    # ══════════════════════════════════════════════════════════════════════════
    #  DRAW
    # ══════════════════════════════════════════════════════════════════════════
    def draw(self):
        # Crear superficie del tamaño correcto
        if self.mode == self.MODE_SPLIT and self.scene not in ["menu", "instructions"]:
            display_w = SPLIT_WIDTH
        else:
            display_w = SCREEN_WIDTH
        
        # Fondo degradado (cielo)
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(SKY_BLUE[0] * (1 - t) + 180 * t)
            g = int(SKY_BLUE[1] * (1 - t) + 220 * t)
            b = int(SKY_BLUE[2] * (1 - t) + 255 * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (display_w, y))

        # Nubes
        for c in self.clouds:
            s = c['size']
            pygame.draw.circle(self.screen, WHITE, (int(c['x']), int(c['y'])), s)
            pygame.draw.circle(self.screen, WHITE, (int(c['x']) + s, int(c['y']) - s // 3), int(s * 0.8))
            pygame.draw.circle(self.screen, WHITE, (int(c['x']) + s * 2, int(c['y'])), s)

        if self.scene == "menu":
            self._draw_menu()
        elif self.scene == "instructions":
            self._draw_instructions()
        elif self.scene in ("game", "pause"):
            self._draw_game()
            if self.scene == "pause":
                self._draw_pause_overlay()
        elif self.scene == "gameover":
            self._draw_game()
            self._draw_gameover_overlay()

        pygame.display.flip()

    # ── Menú ──────────────────────────────────────────────────────────────────
    def _draw_menu(self):
        # Crear superficie según modo
        if self.mode == self.MODE_SPLIT:
            surf = pygame.Surface((SPLIT_WIDTH, SCREEN_HEIGHT))
            # Fondo para ambos lados
            for x_offset in [0, SCREEN_WIDTH + 10]:
                pygame.draw.rect(surf, SKY_BLUE, (x_offset, 0, SCREEN_WIDTH, SCREEN_HEIGHT - 80))
            surf.blit(self.ground, (0, SCREEN_HEIGHT - 80))
            surf.blit(self.ground, (SCREEN_WIDTH + 10, SCREEN_HEIGHT - 80))
            
            # Línea divisoria
            pygame.draw.line(surf, WHITE, (SCREEN_WIDTH + 5, 0), (SCREEN_WIDTH + 5, SCREEN_HEIGHT), 4)
            
            # Etiquetas de jugadores
            j1_label = self.big_font.render("JUGADOR 1", True, (255, 220, 0))
            j2_label = self.big_font.render("JUGADOR 2", True, (70, 130, 255))
            surf.blit(j1_label, ((SCREEN_WIDTH - j1_label.get_width()) // 2, 50))
            surf.blit(j2_label, (SCREEN_WIDTH + 10 + (SCREEN_WIDTH - j2_label.get_width()) // 2, 50))
            
            # Panel central (dividido)
            panel_w = 300
            panel = pygame.Surface((panel_w, 200), pygame.SRCALPHA)
            pygame.draw.rect(panel, (0, 0, 0, 160), (0, 0, panel_w, 200), border_radius=16)
            surf.blit(panel, ((SCREEN_WIDTH - panel_w) // 2, 180))
            
            title = self.font.render("Flappy Hand - 2 JUGADORES", True, GOLD)
            surf.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 200))
            
            self._blit_text_surf(surf, "Jugador 1: Mano IZQUIERDA", self.sm_font, (255, 220, 0), 240, SCREEN_WIDTH // 2 - panel_w // 2)
            self._blit_text_surf(surf, "Jugador 2: Mano DERECHA", self.sm_font, (70, 130, 255), 270, SCREEN_WIDTH // 2 - panel_w // 2)
            self._blit_text_surf(surf, "SPACE = Ver instrucciones", self.sm_font, WHITE, 310, SCREEN_WIDTH // 2 - panel_w // 2)
            
            self.screen.blit(surf, (0, 0))
        else:
            self.screen.blit(self.ground, (0, SCREEN_HEIGHT - 80))

            # Panel central
            panel = pygame.Surface((320, 280), pygame.SRCALPHA)
            pygame.draw.rect(panel, (0, 0, 0, 140), (0, 0, 320, 280), border_radius=16)
            self.screen.blit(panel, (40, 120))

            title = self.big_font.render("Flappy Hand", True, GOLD)
            self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 60))

            self._blit_text("CIERRA la mano para volar", self.sm_font, WHITE, 125)
            self._blit_text("ESPACIO / ENTER = Ver instrucciones", self.sm_font, WHITE, 155)

            # Modo
            mode_names = {
                self.MODE_INFINITE: "INFINITO",
                self.MODE_MISSION: f"MISIÓN ({self.mission_goal} pipes)",
            }
            mode_label = f"Modo: {mode_names.get(self.mode, 'INFINITO')}"
            self._blit_text(mode_label, self.sm_font, CYAN, 190)
            self._blit_text("M – cambiar modo", self.sm_font, (200,200,200), 218)

            # High score
            self._blit_text(f"Récord: {self.high_score}", self.font, GOLD, 260)

    # ── Instrucciones ─────────────────────────────────────────────────────────
    def _draw_instructions(self):
        self.screen.blit(self.ground, (0, SCREEN_HEIGHT - 80))

        # Panel grande
        panel_h = 480 if self.mode == self.MODE_SPLIT else 420
        panel = pygame.Surface((360, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 180), (0, 0, 360, panel_h), border_radius=16)
        self.screen.blit(panel, (20, 40))

        # Título
        title = self.big_font.render("INSTRUCCIONES", True, GOLD)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 20))

        # Instrucciones según modo
        y = 60
        if self.mode == self.MODE_SPLIT:
            self._blit_text("CONTROL 2 JUGADORES:", self.font, CYAN, y)
            y += 35
            self._blit_text("Jugador 1 (Amarillo): Mano IZQUIERDA", self.sm_font, (255, 220, 0), y)
            y += 28
            self._blit_text("Jugador 2 (Azul): Mano DERECHA", self.sm_font, (70, 130, 255), y)
            y += 40
        else:
            self._blit_text("CONTROL CON LA MANO:", self.font, CYAN, y)
            y += 35

        # Estados de la mano con explicación clara
        self._blit_text("DEDOS ABIERTOS = Bajar (sin salto)", self.sm_font, GREEN, y)
        y += 28
        self._blit_text("2-3 DEDOS = Salto suave", self.sm_font, (255, 255, 0), y)
        y += 28
        self._blit_text("PUÑO (0-1 dedo) = Salto fuerte!", self.sm_font, RED, y)
        y += 40

        # Explicación
        self._blit_text("COMO JUGAR:", self.font, CYAN, y)
        y += 35
        instructions = [
            "• Dedos abiertos = el pajaro baja",
            "• Puño = salto fuerte hacia arriba",
            "• 2-3 dedos = salto suave",
            "• Evita chocar con las tuberias",
            "• ¡Sobrevive el mayor tiempo posible!",
        ]
        if self.mode == self.MODE_SPLIT:
            instructions.extend([
            "• Cada jugador tiene su propio pajaro",
            "• ¡El ultimo en caer gana!"
        ])
        for instr in instructions:
            self._blit_text(instr, self.sm_font, WHITE, y)
            y += 26

        y += 15
        # Controles de teclado
        self._blit_text("⌨ ESPACIO = Iniciar | ESC = Volver", self.sm_font, (200,200,200), y)

    # ── Juego ─────────────────────────────────────────────────────────────────
    def _draw_game(self):
        if self.mode == self.MODE_SPLIT:
            self._draw_game_split()
        else:
            self._draw_game_single()

    def _draw_game_single(self):
        # Pipes
        for pipe in self.pipes:
            x, gy, gap = int(pipe['x']), pipe['gap_y'], pipe['gap']
            pygame.draw.rect(self.screen, GREEN,      (x, 0, 52, gy))
            pygame.draw.rect(self.screen, DARK_GREEN, (x - 4, gy - 28, 60, 28),
                             border_radius=4)
            bot = gy + gap
            pygame.draw.rect(self.screen, GREEN,      (x, bot, 52, SCREEN_HEIGHT))
            pygame.draw.rect(self.screen, DARK_GREEN, (x - 4, bot, 60, 28),
                             border_radius=4)

        # Ground
        self.screen.blit(self.ground, (0, SCREEN_HEIGHT - 80))

        # Power-ups
        for pu in self.powerups:
            pu.draw(self.screen, self.sm_font)

        # Pato
        if self.bird:
            self.bird.draw(self.screen)

        # HUD
        self._draw_hud_single()

    def _draw_game_split(self):
        # Crear superficies separadas para cada jugador
        # Jugador 1 (lado izquierdo)
        surf1 = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._draw_game_surface(surf1, self.pipes, self.powerups, self.bird, self.score, (255, 220, 0))
        
        # Jugador 2 (lado derecho)
        surf2 = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._draw_game_surface(surf2, self.pipes2, self.powerups, self.bird2, self.score2, (70, 130, 255))
        
        # Dibujar ambos escenarios lado a lado
        self.screen.blit(surf1, (0, 0))
        self.screen.blit(surf2, (SCREEN_WIDTH + 10, 0))  # 10px de separación
        
        # Línea divisoria
        mid_x = SCREEN_WIDTH + 5
        pygame.draw.line(self.screen, WHITE, (mid_x, 0), (mid_x, SCREEN_HEIGHT), 4)
        
        # HUD
        self._draw_hud_split()

    def _draw_game_surface(self, surface, pipes, powerups, bird, score, player_color):
        # Fondo degradado
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(SKY_BLUE[0] * (1 - t) + 180 * t)
            g = int(SKY_BLUE[1] * (1 - t) + 220 * t)
            b = int(SKY_BLUE[2] * (1 - t) + 255 * t)
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
        # Nubes
        for c in self.clouds:
            s = c['size']
            pygame.draw.circle(surface, WHITE, (int(c['x']), int(c['y'])), s)
            pygame.draw.circle(surface, WHITE, (int(c['x']) + s, int(c['y']) - s // 3), int(s * 0.8))
            pygame.draw.circle(surface, WHITE, (int(c['x']) + s * 2, int(c['y'])), s)
        
        # Pipes
        for pipe in pipes:
            x, gy, gap = int(pipe['x']), pipe['gap_y'], pipe['gap']
            pygame.draw.rect(surface, GREEN, (x, 0, 52, gy))
            pygame.draw.rect(surface, DARK_GREEN, (x - 4, gy - 28, 60, 28), border_radius=4)
            bot = gy + gap
            pygame.draw.rect(surface, GREEN, (x, bot, 52, SCREEN_HEIGHT))
            pygame.draw.rect(surface, DARK_GREEN, (x - 4, bot, 60, 28), border_radius=4)
        
        # Ground
        surface.blit(self.ground, (0, SCREEN_HEIGHT - 80))
        
        # Power-ups
        for pu in powerups:
            pu.draw(surface, self.sm_font)
        
        # Bird
        if bird:
            bird.draw(surface)
        
        # Score en la superficie
        score_txt = self.font.render(str(score), True, WHITE)
        bg_w = max(50, score_txt.get_width() + 20)
        pygame.draw.rect(surface, (0,0,0,160), ((SCREEN_WIDTH - bg_w)//2, 8, bg_w, 38), border_radius=10)
        surface.blit(score_txt, ((SCREEN_WIDTH - score_txt.get_width())//2, 14))

    def _draw_hud_single(self):
        # Score
        score_txt = self.font.render(str(self.score), True, WHITE)
        bg_w = max(50, score_txt.get_width() + 20)
        pygame.draw.rect(self.screen, (0,0,0,160),
                         ((SCREEN_WIDTH - bg_w)//2, 8, bg_w, 38), border_radius=10)
        self.screen.blit(score_txt,
                         ((SCREEN_WIDTH - score_txt.get_width())//2, 14))

        # Vidas (corazones)
        if self.bird:
            for i in range(5):
                color = RED if i < self.bird.lives else (80, 80, 80)
                pygame.draw.polygon(
                    self.screen, color,
                    self._heart_points(10 + i * 22, 18, 8)
                )

        # Modo misión: barra de progreso
        if self.mode == self.MODE_MISSION:
            prog = min(self.score / self.mission_goal, 1.0)
            pygame.draw.rect(self.screen, (60,60,60),
                             (10, SCREEN_HEIGHT - 95, 120, 10), border_radius=5)
            pygame.draw.rect(self.screen, GOLD,
                             (10, SCREEN_HEIGHT - 95, int(120 * prog), 10),
                             border_radius=5)
            lbl = self.sm_font.render(
                f"Misión: {self.score}/{self.mission_goal}", True, WHITE)
            self.screen.blit(lbl, (10, SCREEN_HEIGHT - 112))

        # Slow activo
        if self.slow_timer > 0:
            t = self.sm_font.render(
                f"⏱ Lento {self.slow_timer // 60 + 1}s", True, PURPLE)
            self.screen.blit(t, (SCREEN_WIDTH - t.get_width() - 10, 12))

    def _draw_hud_split(self):
        # Vidas jugador 1 (lado izquierdo)
        if self.bird:
            for i in range(3):
                color = RED if i < self.bird.lives else (80, 80, 80)
                pygame.draw.polygon(
                    self.screen, color,
                    self._heart_points(10 + i * 22, SCREEN_HEIGHT - 25, 8)
                )
        
        # Etiqueta J1
        p1_label = self.font.render("J1", True, (255, 220, 0))
        self.screen.blit(p1_label, (10, 50))
        
        # Vidas jugador 2 (lado derecho)
        if self.bird2:
            for i in range(3):
                color = (70, 130, 255) if i < self.bird2.lives else (80, 80, 80)
                pygame.draw.polygon(
                    self.screen, color,
                    self._heart_points(SCREEN_WIDTH + 20 + i * 22, SCREEN_HEIGHT - 25, 8)
                )
        
        # Etiqueta J2
        p2_label = self.font.render("J2", True, (70, 130, 255))
        self.screen.blit(p2_label, (SCREEN_WIDTH + 20, 50))

    def _heart_points(self, cx, cy, r):
        """Aproximación de corazón con polígono."""
        pts = []
        for i in range(32):
            a = math.radians(i * 360 / 32 - 90)
            x = r * (16 * math.sin(a) ** 3) / 16
            y = -r * (13 * math.cos(a) - 5 * math.cos(2*a)
                      - 2 * math.cos(3*a) - math.cos(4*a)) / 16
            pts.append((int(cx + x), int(cy + y)))
        return pts

    # ── Overlays ──────────────────────────────────────────────────────────────
    def _draw_pause_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 140),
                         (60, 180, 280, 180), border_radius=16)
        self.screen.blit(overlay, (0, 0))
        self._blit_text("PAUSA", self.big_font, WHITE, 198)
        self._blit_text("ESPACIO para continuar", self.sm_font, WHITE, 290)
        self._blit_text("ESC para continuar", self.sm_font, (180,180,180), 316)

    def _draw_gameover_overlay(self):
        if self.mode == self.MODE_SPLIT:
            self._draw_gameover_split()
        else:
            self._draw_gameover_single()

    def _draw_gameover_single(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 170),
                         (50, 170, 300, 240), border_radius=18)
        self.screen.blit(overlay, (0, 0))

        if getattr(self, 'victory', False):
            self._blit_text("¡VICTORIA!", self.big_font, GOLD, 185)
        else:
            self._blit_text("GAME OVER", self.big_font, RED, 185)

        self._blit_text(f"Puntuación: {self.score}", self.font, WHITE, 268)
        self._blit_text(f"Récord: {self.high_score}", self.font, GOLD, 304)
        self._blit_text("ESPACIO para el menú", self.sm_font, GREEN, 352)

    def _draw_gameover_split(self):
        # Overlay en el centro
        overlay = pygame.Surface((400, 200), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 200), (0, 0, 400, 200), border_radius=18)
        
        # Centrar el overlay
        overlay_x = SCREEN_WIDTH - 200
        overlay_y = SCREEN_HEIGHT // 2 - 100
        self.screen.blit(overlay, (overlay_x, overlay_y))

        p1_dead = self.bird and self.bird.state == Bird.STATE_DEAD
        p2_dead = self.bird2 and self.bird2.state == Bird.STATE_DEAD

        if p1_dead and p2_dead:
            self._blit_text("¡EMPATE!", self.big_font, GOLD, overlay_y + 20, overlay_x)
        elif p1_dead:
            self._blit_text("¡J2 GANA!", self.big_font, (70, 130, 255), overlay_y + 20, overlay_x)
        elif p2_dead:
            self._blit_text("¡J1 GANA!", self.big_font, (255, 220, 0), overlay_y + 20, overlay_x)

        self._blit_text(f"J1: {self.score} pts", self.font, (255, 220, 0), overlay_y + 90, overlay_x)
        self._blit_text(f"J2: {self.score2} pts", self.font, (70, 130, 255), overlay_y + 125, overlay_x)
        self._blit_text("ESPACIO para menú", self.sm_font, WHITE, overlay_y + 165, overlay_x)

    # ══════════════════════════════════════════════════════════════════════════
    #  PERSISTENCIA
    # ══════════════════════════════════════════════════════════════════════════
    def _load_high_score(self):
        try:
            with open('high_score.txt', 'r') as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def _save_high_score(self):
        with open('high_score.txt', 'w') as f:
            f.write(str(self.high_score))

    # ══════════════════════════════════════════════════════════════════════════
    #  LOOP PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════
    def run(self):
        import time
        last_log = time.time()
        frame_count = 0
        
        while self.running:
            start = time.time()
            
            self.handle_events()
            handle_time = time.time() - start
            
            update_start = time.time()
            self.update()
            update_time = time.time() - update_start
            
            draw_start = time.time()
            self.draw()
            draw_time = time.time() - draw_start
            
            frame_count += 1
            now = time.time()
            if now - last_log >= 2.0:
                fps = frame_count / (now - last_log)
                print(f"[DEBUG] FPS: {fps:.1f} | handle: {handle_time*1000:.1f}ms | update: {update_time*1000:.1f}ms | draw: {draw_time*1000:.1f}ms | scene: {self.scene}")
                last_log = now
                frame_count = 0
            
            self.clock.tick(FPS)

        self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        cv2.waitKey(1)


# ─── Punto de entrada ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  Flappy Hand – ¡Controla con tu mano!")
    print("=" * 50)
    print("  CIERRA la mano para volar")
    print("  ESPACIO / ENTER  →  iniciar / confirmar")
    print("  ESC              →  pausar / salir")
    print("  M (en menú)      →  cambiar modo de juego")
    print("  Modos: INFINITO | MISIÓN | 2 JUGADORES")
    print("=" * 50)
    Game().run()
import argparse
import heapq
import math
import os
import random
import sys
import time
from array import array
from collections import deque

if "--benchmark" in sys.argv or "--trace" in sys.argv or "--captura" in sys.argv:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

# ==================== CONFIGURAÇÕES ====================
LARGURA, ALTURA = 1050, 680
AREA_W = LARGURA - 260
FPS = 60
RUA_Y, RUA_H = 250, 170
FAIXA_X, FAIXA_W = 580, 95
LINHA_E, LINHA_W = FAIXA_X - 14, FAIXA_X + FAIXA_W + 14
CELULA = 10
GUIA = 42
VEL = 156.0
ACEL, DESACEL, VMAX = 120.0, 260.0, 140.0
ALC, NRAIOS, FOV = 165, 19, math.radians(150)
CUSTO_TATIL = 0.45
INFLACAO = {"solo": 30, "predio": 22, "suspenso": 38}
FASES = [("VERDE", 8.0), ("AMARELO", 2.0), ("TODOS_VERM_1", 1.5), ("PEDESTRE", 9.0), ("TODOS_VERM_2", 1.5)]
ORIGEM = (95, 125)
DESTINOS = {1: ("Mercado", (700, 585)), 2: ("Farmácia", (180, 585)),
            3: ("Padaria", (390, 585)), 4: ("Casa", (700, 125))}
TATIL = [pygame.Rect(40, 120, 720, 10), pygame.Rect(620, 120, 10, 130),
         pygame.Rect(620, 420, 10, 170), pygame.Rect(150, 580, 570, 10)]
LIM = pygame.Rect(10, 28, AREA_W - 20, ALTURA - 56)
N_PEDESTRES = 2

BRANCO, PRETO, ASFALTO = (245, 245, 245), (20, 22, 28), (42, 45, 52)
CALCADA, MEIO_FIO, PISO_TATIL, GRAMA = (130, 134, 142), (175, 180, 188), (235, 190, 20), (46, 115, 65)
AZUL, AZUL_ESC, CABECA = (30, 136, 229), (15, 76, 129), (230, 236, 245)
DOURADO, VERDE, LARANJA, VERMELHO, ROXO = (255, 215, 0), (46, 204, 113), (255, 140, 0), (225, 55, 55), (155, 89, 182)
AMARELO_S = (255, 210, 40)

PALETA_CARROS = [(60, 130, 200), (236, 238, 242), (92, 102, 118), (64, 160, 112), (186, 62, 72), (238, 190, 64)]
ROUPAS = [(220, 80, 80), (80, 140, 220), (240, 190, 60), (90, 180, 120), (170, 100, 200), (235, 235, 235),
          (70, 70, 96), (230, 130, 60)]
CALCAS = [(40, 50, 80), (60, 60, 66), (110, 90, 70), (30, 30, 36), (80, 100, 130)]
CABELOS = [(30, 24, 20), (70, 45, 25), (160, 110, 50), (210, 190, 120), (120, 120, 125), (15, 15, 18)]
PELES = [(240, 200, 165), (220, 170, 130), (180, 125, 90), (130, 85, 60), (95, 62, 45)]

PRESETS = {"dia": (255, 255, 255), "tarde": (255, 192, 150), "noite": (58, 70, 124)}
ROTULO_HORA = {"dia": "Dia", "tarde": "Tarde", "noite": "Noite"}

STATUS = {
    "OCIOSO": "Clique no mapa ou pressione 1-4 para escolher o destino.",
    "NAVEGANDO": "Caminho livre. Seguindo rota A*.",
    "DESVIANDO": "Obstáculo detectado. Desvio local.",
    "AGUARDANDO_SINAL": "Aguardando sinal de pedestres.",
    "ATRAVESSANDO": "Travessia autorizada. Atravessando.",
    "FREIO_EMERGENCIA": "FREIO DE EMERGÊNCIA! Veículo em rota de colisão.",
    "CHEGOU": "Destino alcançado com segurança.",
}

# Fachadas fixas (cenário). Bloqueiam o planejamento, mas não são removíveis.
FACHADAS = [
    dict(tipo="loja", nome="Mercado", rect=pygame.Rect(645, 604, 110, 64), tema=(34, 150, 84),
         claro=(240, 244, 232), icone="cesta"),
    dict(tipo="loja", nome="Farmácia", rect=pygame.Rect(135, 604, 90, 64), tema=(24, 140, 150),
         claro=(236, 244, 246), icone="cruz"),
    dict(tipo="loja", nome="Padaria", rect=pygame.Rect(345, 604, 90, 64), tema=(204, 108, 40),
         claro=(250, 232, 200), icone="pao"),
    dict(tipo="casa", rect=pygame.Rect(50, 34, 76, 50), parede=(240, 214, 160), telhado=(176, 70, 60)),
    dict(tipo="casa", rect=pygame.Rect(140, 34, 76, 50), parede=(170, 200, 225), telhado=(92, 102, 128)),
]
BLOQUEIOS = [f["rect"] for f in FACHADAS]
POSTES_LUZ = [(120, 237, 1), (310, 237, 1), (470, 237, 1), (748, 237, 1),
              (150, 433, -1), (330, 433, -1), (430, 433, -1), (758, 433, -1)]
SEMS = (("carro", FAIXA_X - 42, RUA_Y - 62, -1),
        ("pedestre", FAIXA_X + FAIXA_W + 24, RUA_Y - 48, 1),
        ("carro", FAIXA_X + FAIXA_W + 24, RUA_Y + RUA_H + 10, 1),
        ("pedestre", FAIXA_X - 42, RUA_Y + RUA_H + 10, -1))


def norm(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def na_rua(y):
    return RUA_Y <= y < RUA_Y + RUA_H


def dist_rect(px, py, r):
    return math.hypot(max(r.left - px, 0, px - r.right), max(r.top - py, 0, py - r.bottom))


def limite_travessia():
    return (RUA_H + 24 + GUIA) / VEL * 1.35 + 0.4


def rot(cx, cy, dx, dy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return (int(cx + dx * c - dy * s), int(cy + dx * s + dy * c))


def clamp(v, a, b):
    return a if v < a else b if v > b else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1[:3], c2[:3]))


def tom(c, f):
    return tuple(clamp(int(v * f), 0, 255) for v in c[:3])


def criar_cenario():
    def o(x, y, w, h, tipo, nome, fixo=False):
        return {"rect": pygame.Rect(x, y, w, h), "tipo": tipo, "nome": nome, "fixo": fixo}
    return [
        o(230, 85, 45, 75, "solo", "Banca"),
        o(350, 75, 85, 65, "suspenso", "Copa de árvore"),
        o(690, 200, 32, 32, "solo", "Poste"),
        o(500, 60, 70, 14, "solo", "Caçamba U"),
        o(500, 150, 70, 14, "solo", "Caçamba U"),
        o(556, 60, 14, 104, "solo", "Caçamba U"),
        o(650, 28, 80, 55, "predio", "Casa", True),
        o(300, 470, 40, 40, "solo", "Lixeira"),
        o(460, 470, 90, 55, "suspenso", "Toldo"),
        o(30, 615, 80, 37, "predio", "Prédio", True),
    ]


# ==================== PLANEJAMENTO GLOBAL (A*) ====================
class Grade:
    VIZ = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

    def __init__(self, obstaculos, extras=()):
        self.cols, self.rows = AREA_W // CELULA, ALTURA // CELULA
        self.livre = [[True] * self.cols for _ in range(self.rows)]
        self.custo = [[1.0] * self.cols for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = c * CELULA + 5, r * CELULA + 5
                bloq = x < 16 or x > AREA_W - 16 or y < 44 or y > ALTURA - 44
                if RUA_Y - 20 <= y < RUA_Y + RUA_H + 20 and not (FAIXA_X + 10 <= x <= FAIXA_X + FAIXA_W - 10):
                    bloq = True
                self.livre[r][c] = not bloq
        infl = [o["rect"].inflate(2 * INFLACAO[o["tipo"]], 2 * INFLACAO[o["tipo"]]) for o in obstaculos]
        infl += [e.inflate(12, 12) for e in extras]
        for i in infl:
            r0, r1, c0, c1 = self._celulas(i)
            for r in range(r0, r1 + 1):
                row = self.livre[r]
                for c in range(c0, c1 + 1):
                    row[c] = False
        for t in TATIL:
            r0, r1, c0, c1 = self._celulas(t)
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    self.custo[r][c] = CUSTO_TATIL

    def _celulas(self, rc):
        c0 = max(0, math.ceil((rc.left - 5) / CELULA))
        c1 = min(self.cols - 1, math.ceil((rc.right - 5) / CELULA) - 1)
        r0 = max(0, math.ceil((rc.top - 5) / CELULA))
        r1 = min(self.rows - 1, math.ceil((rc.bottom - 5) / CELULA) - 1)
        return r0, r1, c0, c1

    def celula(self, px, py):
        return (min(max(int(py // CELULA), 0), self.rows - 1), min(max(int(px // CELULA), 0), self.cols - 1))

    def livre_pt(self, px, py):
        r, c = int(py // CELULA), int(px // CELULA)
        return 0 <= r < self.rows and 0 <= c < self.cols and self.livre[r][c]

    def livre_prox(self, rc):
        r, c = rc
        if self.livre[r][c]:
            return rc
        for raio in range(1, 12):
            for dr in range(-raio, raio + 1):
                for dc in range(-raio, raio + 1):
                    rr, cc = r + dr, c + dc
                    if max(abs(dr), abs(dc)) == raio and 0 <= rr < self.rows and 0 <= cc < self.cols \
                            and self.livre[rr][cc]:
                        return (rr, cc)
        return None

    def melhor_celula(self, px, py, raio=12):
        """Centro da célula livre mais próxima (euclidiana) de um ponto."""
        r0, c0 = self.celula(px, py)
        melhor, bd = None, 1e18
        for r in range(max(0, r0 - raio), min(self.rows, r0 + raio + 1)):
            for c in range(max(0, c0 - raio), min(self.cols, c0 + raio + 1)):
                if self.livre[r][c]:
                    x, y = c * CELULA + 5, r * CELULA + 5
                    d = (x - px) ** 2 + (y - py) ** 2
                    if d < bd:
                        bd, melhor = d, (x, y)
        return melhor

    def pontos_calcada(self):
        """Pontos livres 'folgados' das calçadas norte e sul (metas dos pedestres)."""
        norte, sul = [], []
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                if not all(self.livre[r + dr][c + dc] for dr in (-1, 0, 1) for dc in (-1, 0, 1)):
                    continue
                x, y = c * CELULA + 5, r * CELULA + 5
                if y < RUA_Y - 30:
                    norte.append((x, y))
                elif y > RUA_Y + RUA_H + 30:
                    sul.append((x, y))
        return norte, sul

    def buscar(self, p0, p1):
        s, g = self.livre_prox(self.celula(*p0)), self.livre_prox(self.celula(*p1))
        if s is None or g is None:
            return None

        def h(n):
            dr, dc = abs(n[0] - g[0]), abs(n[1] - g[1])
            return CUSTO_TATIL * (dr + dc + (math.sqrt(2) - 2) * min(dr, dc))

        aberto, custo, pai, fechado = [(h(s), s)], {s: 0.0}, {}, set()
        while aberto:
            _, n = heapq.heappop(aberto)
            if n in fechado:
                continue
            if n == g:
                break
            fechado.add(n)
            for dr, dc in self.VIZ:
                r, c = n[0] + dr, n[1] + dc
                if not (0 <= r < self.rows and 0 <= c < self.cols) or not self.livre[r][c]:
                    continue
                if dr and dc and not (self.livre[n[0] + dr][n[1]] and self.livre[n[0]][n[1] + dc]):
                    continue
                ng = custo[n] + (1.4142 if dr and dc else 1.0) * self.custo[r][c]
                if ng < custo.get((r, c), 1e18):
                    custo[(r, c)], pai[(r, c)] = ng, n
                    heapq.heappush(aberto, (ng + h((r, c)), (r, c)))
        else:
            return None
        caminho, n = [], g
        while n in pai:
            caminho.append((n[1] * CELULA + 5, n[0] * CELULA + 5))
            n = pai[n]
        caminho.append((s[1] * CELULA + 5, s[0] * CELULA + 5))
        return caminho[::-1]

    def superficie(self):
        surf = pygame.Surface((AREA_W, ALTURA), pygame.SRCALPHA)
        for r in range(self.rows):
            for c in range(self.cols):
                if not self.livre[r][c]:
                    surf.fill((225, 55, 55, 70), (c * CELULA, r * CELULA, CELULA, CELULA))
        return surf


# ==================== ENTIDADES ====================
class Semaforo:
    def __init__(self):
        self.i, self.t = 0, 0.0

    @property
    def nome(self):
        return FASES[self.i][0]

    @property
    def restante(self):
        return FASES[self.i][1] - self.t

    def atualizar(self, dt):
        self.t += dt
        while self.t >= FASES[self.i][1]:
            self.t -= FASES[self.i][1]
            self.i = (self.i + 1) % len(FASES)

    def tempo_ate(self, alvo):
        """Segundos até o início da fase `alvo` (0 se já estiver nela)."""
        if self.nome == alvo:
            return 0.0
        total, i = self.restante, (self.i + 1) % len(FASES)
        while FASES[i][0] != alvo:
            total += FASES[i][1]
            i = (i + 1) % len(FASES)
        return total

    def cont_carro(self):
        n = self.nome
        if n == "VERDE":
            return self.restante, VERDE
        if n == "AMARELO":
            return self.restante, AMARELO_S
        return self.tempo_ate("VERDE"), VERMELHO

    def cont_pedestre(self):
        if self.nome == "PEDESTRE":
            return self.restante, VERDE
        return self.tempo_ate("PEDESTRE"), VERMELHO


class Veiculo:
    _id = 0

    def __init__(self, faixa, infrator, x):
        Veiculo._id += 1
        self.id, self.faixa, self.infrator = Veiculo._id, faixa, infrator
        self.dir = 1 if faixa == 0 else -1
        self.x, self.y = x, RUA_Y + (42 if faixa == 0 else 128)
        self.v, self.a = VMAX, 0.0
        self.cor = PALETA_CARROS[self.id % len(PALETA_CARROS)]

    def rect(self):
        return pygame.Rect(int(self.x - 28), int(self.y - 14), 56, 28)

    def varrido(self, dt=1.0):
        r = self.rect()
        return r.union(r.move(int(self.dir * self.v * dt), 0))

    def atualizar(self, dt, sem, faixa, pessoas):
        if dt <= 0:
            return
        f = self.dir
        frente = self.x + f * 28
        d_linha = (LINHA_E - frente) if f == 1 else (frente - LINHA_W)
        v_des = VMAX
        if not self.infrator and sem.nome != "VERDE" and d_linha > -2:
            if sem.nome != "AMARELO" or d_linha > self.v ** 2 / (2 * DESACEL):
                v_des = min(v_des, math.sqrt(2 * 0.8 * DESACEL * max(d_linha - 2, 0)))
        gap, v_lider = 1e9, 0.0
        for o in faixa:
            if o is not self and (o.x - self.x) * f > 0:
                g = (o.x - self.x) * f - 56
                if g < gap:
                    gap, v_lider = g, o.v
        for p in pessoas:
            if p.top < self.y + 20 and p.bottom > self.y - 20:
                g = (p.centerx - self.x) * f - 28 - p.w / 2
                if -5 < g < gap and (not self.infrator or g < 40):
                    gap, v_lider = g, 0.0
        if gap < 1e8:
            v_des = min(v_des, v_lider + math.sqrt(2 * 0.8 * DESACEL * max(gap - 18, 0)))
        dv = max(-DESACEL * dt, min(ACEL * dt, v_des - self.v))
        self.a = dv / dt
        self.v = max(0.0, self.v + dv)
        self.x += f * self.v * dt


class Pedestre:
    """Pessoa que caminha pelas calçadas e atravessa na faixa quando o sinal permite."""
    raio = 7

    def __init__(self, rng, x, y):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.vel = rng.uniform(30, 46)
        self.ang = rng.uniform(-math.pi, math.pi)
        self.rota, self.estado = [], "PARADO"
        self.espera = rng.uniform(0.0, 2.0)
        self.fase = rng.uniform(0, 6.28)
        self.ref, self.t_ref = (x, y), 0.0
        self.cores = (rng.choice(ROUPAS), rng.choice(CALCAS), rng.choice(CABELOS), rng.choice(PELES))
        self.acessorio = rng.choice([None, None, "mochila", "chapeu"])

    def rect(self):
        return pygame.Rect(int(self.x - 7), int(self.y - 7), 14, 14)


class Tutor:
    raio = 12

    def __init__(self, x, y):
        self.x, self.y, self.tensao = x, y, 0.0

    def mover(self, robo, solidos, dt):
        dx, dy = robo.x - self.x, robo.y - self.y
        d = math.hypot(dx, dy)
        if d > GUIA + 0.5:
            s = min(VEL * 1.25, (d - GUIA) * 30) * dt
            nx, ny = self.x + dx / d * s, self.y + dy / d * s
            for cx, cy in ((nx, ny), (nx, self.y), (self.x, ny)):
                if not any(o.inflate(2 * self.raio, 2 * self.raio).collidepoint(cx, cy) for o in solidos):
                    self.x, self.y = cx, cy
                    break
        self.tensao = max(0.0, math.hypot(robo.x - self.x, robo.y - self.y) - GUIA)

    def rect(self):
        return pygame.Rect(int(self.x - self.raio), int(self.y - self.raio), 2 * self.raio, 2 * self.raio)


class Robo:
    raio = 16

    def __init__(self, x, y):
        self.x, self.y, self.angulo, self.v, self.passo = x, y, 0.0, 0.0, 0.0
        self.hist = [deque(maxlen=3) for _ in range(NRAIOS)]
        self.filtrado = []

    def rect(self):
        return pygame.Rect(int(self.x - self.raio), int(self.y - self.raio), 2 * self.raio, 2 * self.raio)

    def escanear(self, alvos, rng):
        bbox = pygame.Rect(self.x - ALC, self.y - ALC, 2 * ALC, 2 * ALC)
        perto = [(r, t) for r, t in alvos if r.colliderect(bbox)]
        p0 = (self.x, self.y)
        self.filtrado = []
        for i in range(NRAIOS):
            ang = self.angulo - FOV / 2 + i * FOV / (NRAIOS - 1)
            p1 = (self.x + math.cos(ang) * ALC, self.y + math.sin(ang) * ALC)
            d, tipo = float(ALC), None
            c = LIM.clipline(p0, p1)
            if c:
                dw = max(math.dist(p0, c[0]), math.dist(p0, c[1]))
                if dw < ALC - 1:
                    d, tipo = dw, "parede"
            for r, t in perto:
                c = r.clipline(p0, p1)
                if c:
                    dr = min(math.dist(p0, c[0]), math.dist(p0, c[1]))
                    if dr < d:
                        d, tipo = dr, t
            d = min(max(d + rng.gauss(0, 1.5), 0.0), ALC)
            if rng.random() < 0.02:
                d, tipo = float(ALC), None
            self.hist[i].append((d, tipo))
            med = sorted(self.hist[i], key=lambda e: e[0])[len(self.hist[i]) // 2]
            self.filtrado.append((ang, med[0], med[1]))

    def setores(self):
        cen = esq = dir_ = float(ALC)
        melhor = (ALC, 0.0)
        for ang, d, tipo in self.filtrado:
            if tipo == "veiculo":
                continue
            rel = norm(ang - self.angulo)
            if abs(rel) <= math.radians(25):
                cen = min(cen, d)
            elif rel < 0:
                esq = min(esq, d)
            else:
                dir_ = min(dir_, d)
            if d < melhor[0]:
                melhor = (d, rel)
        return cen, esq, dir_, math.sin(melhor[1])


# ==================== MUNDO / SIMULAÇÃO ====================
OFFS_DIR = (0, .3, -.3, .6, -.6, 1.0, -1.0, 1.5, -1.5, 2.2, -2.2)


class Mundo:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.rng_ped = random.Random(None if seed is None else seed + 7919)
        self.obstaculos = criar_cenario()
        self.grade = Grade(self.obstaculos, BLOQUEIOS)
        self.pontos = self.grade.pontos_calcada()
        self.sem = Semaforo()
        self.veiculos = []
        self.t_spawn = [0.5, 1.0]
        self.robo = Robo(*ORIGEM)
        self.tutor = Tutor(ORIGEM[0] - GUIA, ORIGEM[1])
        self.estado, self.fase, self.dest = "OCIOSO", "IDA", None
        self.rotulo = "-"
        self.alvo, self.caminho, self.idx = ORIGEM, None, 0
        self.autorizado = self.entrou = self.concluida = False
        self.t_freio = self.t_chegou = self.t_preso = self.t_bip = self.tempo = 0.0
        self.nivel, self.pan, self.bip = 0, 0.0, None
        self.contato, self.proximo, self.log = set(), set(), []
        self.replans = 0
        self.met = dict(tempo=0.0, dist=0.0, alertas=0, freios=0, viagens=0, colisoes=0, quase=0)
        self.pedestres = []
        for i in range(N_PEDESTRES):
            pts = self.pontos[i % 2]
            for _ in range(10):
                x, y = self.rng_ped.choice(pts)
                if math.hypot(x - ORIGEM[0], y - ORIGEM[1]) > 70:
                    break
            self.pedestres.append(Pedestre(self.rng_ped, x, y))

    def mudar(self, novo, motivo=""):
        if novo != self.estado:
            self.log.append((self.tempo, self.estado, novo, motivo))
            self.estado = novo

    def planejar(self):
        self.caminho = self.grade.buscar((self.robo.x, self.robo.y), self.alvo)
        self.idx, self.t_preso = 0, 0.0
        if self.caminho is None:
            self.mudar("OCIOSO", "sem rota")

    def iniciar_viagem(self, d):
        self.dest, self.fase, self.alvo, self.concluida = d, "IDA", DESTINOS[d][1], False
        self.rotulo = DESTINOS[d][0]
        self.autorizado = False
        self.planejar()
        if self.caminho:
            self.mudar("NAVEGANDO", f"destino {d} ({DESTINOS[d][0]}) escolhido; rota A* planejada")

    def ir_para(self, x, y):
        """Clique no cenário: caminha até o ponto livre mais próximo, desviando de obstáculos."""
        for k, (nome, (dx, dy)) in DESTINOS.items():
            if math.hypot(x - dx, y - dy) < 22:
                self.iniciar_viagem(k)
                return f"Rota para {nome}"
        c = self.grade.melhor_celula(x, y, 14)
        if c is None:
            return "Local inacessível"
        msg = None
        if math.hypot(c[0] - x, c[1] - y) > 25:
            msg = "Via de veículos/obstáculo: indo ao ponto seguro mais próximo"
        anterior = (self.dest, self.fase, self.alvo, self.rotulo)
        self.dest, self.fase, self.alvo, self.concluida = None, "IDA", c, False
        self.rotulo = "Ponto no mapa"
        if not (na_rua(self.robo.y) or na_rua(self.tutor.y)):
            self.autorizado = False
        self.planejar()
        if not self.caminho:
            self.dest, self.fase, self.alvo, self.rotulo = anterior
            return "Sem rota até esse ponto"
        self.mudar("NAVEGANDO", "clique no mapa; rota A* planejada")
        return msg

    def obstaculo_em(self, x, y):
        for o in reversed(self.obstaculos):
            if o["rect"].collidepoint(x, y):
                return o
        for o in reversed(self.obstaculos):
            if o["rect"].inflate(8, 8).collidepoint(x, y):
                return o
        return None

    def reconstruir_grade(self):
        self.grade = Grade(self.obstaculos, BLOQUEIOS)
        self.pontos = self.grade.pontos_calcada()
        for p in self.pedestres:
            if not self.grade.livre_pt(p.x, p.y) and p.estado != "ATRAVESSANDO":
                c = self.grade.melhor_celula(p.x, p.y, 8)
                if c:
                    p.x, p.y = c
        if self.estado not in ("OCIOSO", "CHEGOU"):
            self.planejar()

    def adicionar_obstaculo(self, x, y):
        if RUA_Y - 30 <= y <= RUA_Y + RUA_H + 30:
            return "Não é possível criar obstáculos na via"
        novo = pygame.Rect(x - 22, y - 22, 44, 44)
        if novo.colliderect(self.robo.rect().inflate(10, 10)) or novo.colliderect(self.tutor.rect().inflate(10, 10)):
            return "Muito perto do robô"
        self.obstaculos.append({"rect": novo, "tipo": self.rng.choice(["solo", "suspenso"]),
                                "nome": "Obstáculo", "fixo": False})
        self.reconstruir_grade()
        return "Obstáculo criado"

    def alternar_obstaculo(self, x, y):
        """Botão direito: remove SÓ o objeto clicado; em área vazia cria um obstáculo."""
        o = self.obstaculo_em(x, y)
        if o is None:
            return self.adicionar_obstaculo(x, y)
        if o.get("fixo"):
            return f"{o['nome']} é fixo e não pode ser removido"
        self.obstaculos.remove(o)
        self.reconstruir_grade()
        return f"Removido: {o['nome']}"

    # ---------- tráfego ----------
    def atualizar_trafego(self, dt):
        for f in (0, 1):
            self.t_spawn[f] -= dt
            if self.t_spawn[f] <= 0:
                x0 = -40 if f == 0 else AREA_W + 40
                if all(abs(v.x - x0) > 110 for v in self.veiculos if v.faixa == f):
                    self.veiculos.append(Veiculo(f, self.rng.random() < 0.15, x0))
                    self.t_spawn[f] = self.rng.uniform(1.5, 4.0)
                else:
                    self.t_spawn[f] = 0.3
        pessoas = [self.robo.rect(), self.tutor.rect()] + [p.rect() for p in self.pedestres]
        for v in self.veiculos:
            v.atualizar(dt, self.sem, [o for o in self.veiculos if o.faixa == v.faixa], pessoas)
        self.veiculos = [v for v in self.veiculos if -90 < v.x < AREA_W + 90]

    # ---------- pedestres ----------
    def nova_rota(self, p):
        rng = self.rng_ped
        lado = 0 if p.y < RUA_Y else 1
        lado_meta = lado if rng.random() < 0.72 else 1 - lado
        pts = self.pontos[lado_meta]
        g = rng.choice(pts)
        for _ in range(8):
            g = rng.choice(pts)
            if lado_meta != lado or math.hypot(g[0] - p.x, g[1] - p.y) > 90:
                break
        rota = []
        if lado_meta != lado:
            cx = rng.uniform(FAIXA_X + 16, FAIXA_X + 56)
            ya = RUA_Y - 26 if lado == 0 else RUA_Y + RUA_H + 26
            yb = RUA_Y + RUA_H + 26 if lado == 0 else RUA_Y - 26
            rota = [(cx, ya, "espera"), (cx, yb, "cruz")]
        rota.append((g[0], g[1], "fim"))
        p.rota, p.estado, p.t_ref, p.ref = rota, "ANDANDO", 0.0, (p.x, p.y)

    def _direcao(self, p, ang0, agentes):
        melhor, mc = ang0, 1e18
        livre = self.grade.livre_pt
        for off in OFFS_DIR:
            a = ang0 + off
            ca, sa = math.cos(a), math.sin(a)
            c = abs(off) * 12 + abs(norm(a - p.ang)) * 4
            for dist, w in ((8, 400), (16, 60), (26, 14)):
                if not livre(p.x + ca * dist, p.y + sa * dist):
                    c += w
            qx, qy = p.x + ca * 22, p.y + sa * 22
            for ax, ay, ar, o in agentes:
                if o is p:
                    continue
                dd = math.hypot(qx - ax, qy - ay)
                lim = ar + p.raio + 12
                if dd < lim:
                    c += (lim - dd) * 5
            if c < mc:
                mc, melhor = c, a
        return melhor

    def _posicao_pedestre_valida(self, p, x, y):
        """Impede que pedestres fora da travessia sejam deslocados para a pista."""
        if not (20 <= x <= AREA_W - 20 and 36 <= y <= ALTURA - 36):
            return False

        if p.estado == "ATRAVESSANDO":
            return (
                FAIXA_X + 14 <= x <= FAIXA_X + FAIXA_W - 14
                and RUA_Y - 30 <= y <= RUA_Y + RUA_H + 30
            )

        return not na_rua(y) and self.grade.livre_pt(x, y)

    def _separar(self, p, agentes):
        for ax, ay, ar, o in agentes:
            if o is p:
                continue

            ex, ey = p.x - ax, p.y - ay
            dd = math.hypot(ex, ey)
            mn = p.raio + ar + 1

            if 0 < dd < mn:
                push = mn - dd
                if isinstance(o, Pedestre):
                    push *= 0.5

                nx = p.x + ex / dd * push
                ny = p.y + ey / dd * push

                # A separação nunca pode jogar alguém na pista por acidente.
                if self._posicao_pedestre_valida(p, nx, ny):
                    p.x, p.y = nx, ny

    def mover_pedestre(self, p, dt, agentes):
        if p.estado == "PARADO":
            p.espera -= dt
            p.vx *= 0.8
            p.vy *= 0.8
            self._separar(p, agentes)
            if p.espera <= 0:
                self.nova_rota(p)
            return
        if not p.rota:
            p.estado, p.espera = "PARADO", self.rng_ped.uniform(1.0, 4.0)
            return
        if p.estado == "ESPERANDO":
            if self.sem.nome == "PEDESTRE" and self.sem.restante > 5.0 and self.faixa_livre():
                p.estado = "ATRAVESSANDO"
            else:
                p.vx *= 0.7
                p.vy *= 0.7
                self._separar(p, agentes)
                return
        tx, ty, tag = p.rota[0]
        dx, dy = tx - p.x, ty - p.y
        d = math.hypot(dx, dy)
        if d < (10 if tag == "fim" else 8):
            p.rota.pop(0)
            if tag == "espera":
                p.estado = "ESPERANDO"
            elif tag == "cruz":
                p.estado = "ANDANDO"
            else:
                p.estado, p.espera = "PARADO", self.rng_ped.uniform(1.0, 4.0)
            return
        ang0 = math.atan2(dy, dx)
        cruz = p.estado == "ATRAVESSANDO"
        vel = max(p.vel, 50.0) if cruz else p.vel
        ang = ang0 if cruz else self._direcao(p, ang0, agentes)
        p.ang += norm(ang - p.ang) * min(1.0, dt * 8)
        fator = 1.0
        ca, sa = math.cos(p.ang), math.sin(p.ang)
        for ax, ay, ar, o in agentes:
            if o is p:
                continue
            ex, ey = ax - p.x, ay - p.y
            dd = math.hypot(ex, ey)
            if dd < ar + p.raio + 16 and ex * ca + ey * sa > 0:
                fator = min(fator, max(0.25, (dd - ar - p.raio) / 16))
        dvx, dvy = ca * vel * fator, sa * vel * fator
        k = min(1.0, dt * 6)
        p.vx += (dvx - p.vx) * k
        p.vy += (dvy - p.vy) * k
        nx, ny = p.x + p.vx * dt, p.y + p.vy * dt
        if cruz:
            # Durante a travessia, o pedestre permanece dentro dos limites da faixa.
            nx = clamp(nx, FAIXA_X + 14, FAIXA_X + FAIXA_W - 14)
            ny = clamp(ny, RUA_Y - 30, RUA_Y + RUA_H + 30)
            if self._posicao_pedestre_valida(p, nx, ny):
                p.x, p.y = nx, ny
            else:
                p.vx = p.vy = 0.0
        elif not na_rua(ny) and self.grade.livre_pt(nx, ny):
            p.x, p.y = nx, ny
        elif not na_rua(p.y) and self.grade.livre_pt(nx, p.y):
            p.x, p.vy = nx, 0.0
        elif not na_rua(ny) and self.grade.livre_pt(p.x, ny):
            p.y, p.vx = ny, 0.0
        else:
            p.vx = p.vy = 0.0
        self._separar(p, agentes)
        p.fase += math.hypot(p.vx, p.vy) * dt * 0.3
        p.t_ref += dt
        if p.t_ref > 2.5:
            if p.estado == "ANDANDO" and math.hypot(p.x - p.ref[0], p.y - p.ref[1]) < 8:
                self.nova_rota(p)
            p.ref, p.t_ref = (p.x, p.y), 0.0

    def atualizar_pedestres(self, dt):
        agentes = [(self.robo.x, self.robo.y, 16, self.robo), (self.tutor.x, self.tutor.y, 12, self.tutor)]
        agentes += [(p.x, p.y, p.raio, p) for p in self.pedestres]
        for p in self.pedestres:
            self.mover_pedestre(p, dt, agentes)

    def alvos_lidar(self):
        return ([(o["rect"], o["tipo"]) for o in self.obstaculos] + [(v.rect(), "veiculo") for v in self.veiculos]
                + [(p.rect(), "pessoa") for p in self.pedestres])

    # ---------- segurança ----------
    def prever_colisao(self):
        corpos = [self.robo.rect().inflate(8, 8), self.tutor.rect().inflate(8, 8)]
        return any(v.v > 5 and any(v.varrido(1.0).colliderect(c) for c in corpos) for v in self.veiculos)

    def veiculo_a_frente(self):
        r = self.robo
        return any(t == "veiculo" and d < 22 and abs(norm(a - r.angulo)) <= math.radians(20)
                   for a, d, t in r.filtrado)

    def faixa_livre(self):
        zona = pygame.Rect(FAIXA_X, RUA_Y, FAIXA_W, RUA_H)
        t_cruz = (RUA_H + 24 + GUIA) / VEL + 0.6
        for v in self.veiculos:
            if v.rect().colliderect(zona):
                return False
            d = (FAIXA_X - (v.x + 28)) if v.dir == 1 else ((v.x - 28) - (FAIXA_X + FAIXA_W))
            if d > 0 and v.v > 5 and v.a > -40 and d < 320 and d / v.v < t_cruz:
                return False
        return True

    def pode_atravessar(self):
        return self.sem.nome == "PEDESTRE" and self.sem.restante > limite_travessia() and self.faixa_livre()

    def entrando_na_rua(self):
        r = self.robo
        if na_rua(r.y) or not self.caminho:
            return False
        for w in self.caminho[self.idx:self.idx + 6]:
            if na_rua(w[1]):
                return math.hypot(w[0] - r.x, w[1] - r.y) < 45 and min(abs(r.y - RUA_Y), abs(r.y - RUA_Y - RUA_H)) < 30
        return False

    def aplicar_barreira(self, ent, x0, y0):
        if na_rua(ent.y):
            ent.x = min(max(ent.x, FAIXA_X + 10), FAIXA_X + FAIXA_W - 10) if na_rua(y0) or self.autorizado else ent.x
        if na_rua(ent.y) and not na_rua(y0):
            if not (self.autorizado and FAIXA_X + 8 <= ent.x <= FAIXA_X + FAIXA_W - 8):
                ent.x, ent.y = x0, y0
        ent.x = min(max(ent.x, 20), AREA_W - 20)
        ent.y = min(max(ent.y, 36), ALTURA - 36)

    # ---------- navegação ----------
    def seguir(self, dt):
        r, c = self.robo, self.caminho
        while self.idx < len(c) - 1 and math.hypot(c[self.idx][0] - r.x, c[self.idx][1] - r.y) < 16:
            self.idx += 1
        wp = c[min(self.idx + 2, len(c) - 1)]
        diff = norm(math.atan2(wp[1] - r.y, wp[0] - r.x) - r.angulo)
        if abs(diff) > 1.0:
            r.angulo += max(-3.5 * dt, min(3.5 * dt, diff))
            return 0.0, False
        cen, esq, dir_, _ = r.setores()
        if cen < 50:
            r.angulo += (-1 if esq > dir_ else 1) * 2.4 * dt
            return VEL * 0.35 * max(0.0, (cen - 36) / 14), True
        if esq < 22 or dir_ < 22:
            r.angulo += (1 if esq < dir_ else -1) * 1.5 * dt
            return VEL * 0.8, True
        r.angulo += max(-3.5 * dt, min(3.5 * dt, diff))
        return VEL * max(0.3, math.cos(diff)), False

    def finalizar_chegada(self):
        if self.dest is not None and self.fase == "IDA":
            self.fase, self.alvo = "VOLTA", ORIGEM
            self.planejar()
            self.mudar("NAVEGANDO", "retorno à origem; nova rota A*")
        else:
            if self.dest is not None:
                self.met["viagens"] += 1
            self.concluida = True
            self.mudar("OCIOSO", "viagem de ida e volta concluída" if self.dest is not None
                       else "ponto escolhido alcançado")

    def passo(self, dt):
        r, t = self.robo, self.tutor
        self.tempo += dt
        self.sem.atualizar(dt)
        self.atualizar_trafego(dt)
        self.atualizar_pedestres(dt)
        r.escanear(self.alvos_lidar(), self.rng)
        cen, esq, dir_, pan = r.setores()
        if self.prever_colisao() or self.veiculo_a_frente():
            self.t_freio = 0.4
        elif self.t_freio > 0:
            self.t_freio -= dt
        freio = self.t_freio > 0
        cmd, desviando, gate = 0.0, False, False
        if self.estado == "CHEGOU":
            self.t_chegou -= dt
            if self.t_chegou <= 0:
                self.finalizar_chegada()
        elif self.estado != "OCIOSO" and self.caminho:
            self.met["tempo"] += dt
            if self.autorizado:
                self.entrou = self.entrou or na_rua(r.y)
                if self.entrou and not na_rua(r.y) and not na_rua(t.y):
                    self.autorizado = False
            gate = not self.autorizado and self.entrando_na_rua()
            if gate and self.pode_atravessar():
                self.autorizado, self.entrou, gate = True, False, False
            cmd, desviando = self.seguir(dt)
            if math.hypot(r.x - self.alvo[0], r.y - self.alvo[1]) < 18 and not self.autorizado:
                self.t_chegou = 1.5 if self.fase == "IDA" else 0.5
                self.mudar("CHEGOU", f"chegou ao alvo ({self.fase})")
                cmd = 0.0
            elif freio:
                self.mudar("FREIO_EMERGENCIA", "swept volume de veículo intercepta robô/tutor")
            elif self.autorizado:
                self.mudar("ATRAVESSANDO", "PEDESTRE e tempo_restante > limite; faixa livre")
            elif gate:
                self.mudar("AGUARDANDO_SINAL", f"meio-fio e sinal em {self.sem.nome}")
            elif desviando:
                self.mudar("DESVIANDO", "obstáculo no LiDAR filtrado")
            else:
                self.mudar("NAVEGANDO", "caminho livre / retomou rota")
            if self.estado in ("NAVEGANDO", "DESVIANDO") and (desviando or r.v < 15):
                self.t_preso += dt
                if self.t_preso > 3.5:
                    self.replans += 1
                    self.planejar()
            else:
                self.t_preso = max(0.0, self.t_preso - dt)
        if freio or gate:
            cmd = 0.0
        cmd *= 1.0 if t.tensao <= 10 else max(0.15, 1 - (t.tensao - 10) / 25)
        r.v += max(-(900 if freio else 500) * dt, min(300 * dt, cmd - r.v))
        x0, y0, tx0, ty0 = r.x, r.y, t.x, t.y
        r.x += math.cos(r.angulo) * r.v * dt
        r.y += math.sin(r.angulo) * r.v * dt
        self.aplicar_barreira(r, x0, y0)
        t.mover(r, [o["rect"] for o in self.obstaculos], dt)
        self.aplicar_barreira(t, tx0, ty0)
        r.passo += r.v * dt * 0.08
        self.met["dist"] += math.hypot(r.x - x0, r.y - y0)
        self.contabilizar(dt, freio, cen, esq, dir_, pan)

    def contabilizar(self, dt, freio, cen, esq, dir_, pan):
        for nome, e in (("R", self.robo), ("T", self.tutor)):
            for o in self.obstaculos:
                k = (nome, "o", id(o))
                if dist_rect(e.x, e.y, o["rect"]) < e.raio:
                    if k not in self.contato:
                        self.contato.add(k)
                        self.met["colisoes"] += 1
                else:
                    self.contato.discard(k)
            for v in self.veiculos:
                d = dist_rect(e.x, e.y, v.rect())
                k = (nome, "v", v.id)
                if d < e.raio:
                    if k not in self.contato:
                        self.contato.add(k)
                        self.met["colisoes"] += 1
                else:
                    self.contato.discard(k)
                if e.raio <= d < e.raio + 15 and v.v > 8:
                    if k not in self.proximo:
                        self.proximo.add(k)
                        self.met["quase"] += 1
                elif d > e.raio + 60:
                    self.proximo.discard(k)
        nivel = 2 if (freio or cen < 50) else 1 if (cen < 85 or min(esq, dir_) < 45) else 0
        if freio and self.nivel < 2 and self.estado == "FREIO_EMERGENCIA":
            self.met["freios"] += 1 if not getattr(self, "_em_freio", False) else 0
        self._em_freio = freio
        if nivel == 2 and self.nivel < 2:
            self.met["alertas"] += 1
        self.t_bip -= dt
        if nivel > 0 and (nivel > self.nivel or (nivel == 2 and self.t_bip <= 0)):
            self.bip, self.t_bip = (1000 if nivel == 2 else 660, pan), 0.7
        self.nivel, self.pan = nivel, pan


# ==================== BENCHMARK ====================
def rodar_viagem(m, dest, limite=150.0, dt=1 / 60):
    t0 = m.tempo
    m.iniciar_viagem(dest)
    while not m.concluida and m.tempo - t0 < limite:
        if m.estado == "OCIOSO":
            break
        m.passo(dt)
    ok = m.concluida
    if not ok:
        m.robo, m.tutor = Robo(*ORIGEM), Tutor(ORIGEM[0] - GUIA, ORIGEM[1])
        m.autorizado, m.estado = False, "OCIOSO"
    return ok, m.tempo - t0


def benchmark(n, seed):
    m = Mundo(seed)
    ok_t = []
    for _ in range(n):
        ok, t = rodar_viagem(m, m.rng.choice([1, 2, 3, 4]))
        if ok:
            ok_t.append(t)
    sucesso = len(ok_t)
    print(f"=== DOG-IA V2 | benchmark {n} viagens | seed {seed} ===")
    print(f"Taxa de sucesso: {sucesso}/{n} ({100 * sucesso / n:.1f}%)")
    print(f"Tempo médio por viagem (ida+volta): {sum(ok_t) / max(1, sucesso):.1f} s")
    print(f"Distância total percorrida: {m.met['dist']:.0f} px")
    print(f"Colisões: {m.met['colisoes']} | Quase-colisões: {m.met['quase']}")
    print(f"Alertas vermelhos: {m.met['alertas']} | Freios de emergência: {m.met['freios']}")
    print(f"Replanejamentos por desvio preso: {m.replans}")


def trace(seed):
    m = Mundo(seed)
    ok, t = rodar_viagem(m, 1)
    print(f"Viagem ao Mercado (seed {seed}): {'concluída' if ok else 'FALHOU'} em {t:.1f} s")
    for tempo, a, b, motivo in m.log:
        print(f"[{tempo:6.2f}s] {a:17s} -> {b:17s} | {motivo}")


# ==================== ÁUDIO ESTÉREO ====================
_cache_audio = {}


def tocar_bip(freq, pan):
    if not pygame.mixer.get_init():
        return
    chave = (freq, round(pan, 1))
    if chave not in _cache_audio:
        taxa, n = 22050, int(22050 * 0.12)
        pan = clamp(pan, -1.0, 1.0)
        gl, gr = math.sqrt((1 - pan) / 2), math.sqrt((1 + pan) / 2)
        buf = array("h")
        for i in range(n):
            s = math.sin(2 * math.pi * freq * i / taxa) * 0.4 * 32767 * min(1, i / 200, (n - i) / 200)
            buf.append(int(s * gl))
            buf.append(int(s * gr))
        _cache_audio[chave] = pygame.mixer.Sound(buffer=buf.tobytes())
    _cache_audio[chave].play()


# ==================== UTILIDADES VISUAIS ====================
def gradiente_v(s, r, c1, c2):
    r = pygame.Rect(r)
    for i in range(r.h):
        pygame.draw.line(s, mix(c1, c2, i / max(1, r.h - 1)), (r.x, r.y + i), (r.right - 1, r.y + i))


def sombra(s, rect, dx=5, dy=7, alpha=70, raio=6, elipse=False):
    r = pygame.Rect(rect).move(dx, dy)
    if r.w <= 0 or r.h <= 0:
        return
    t = pygame.Surface(r.size, pygame.SRCALPHA)
    if elipse:
        pygame.draw.ellipse(t, (0, 0, 0, alpha), t.get_rect())
    else:
        pygame.draw.rect(t, (0, 0, 0, alpha), t.get_rect(), border_radius=raio)
    s.blit(t, r.topleft)


_glows, _glows_r, _tmps, _txt, _sprites = {}, {}, {}, {}, {}


def glow(raio, cor, nivel=5):
    k = (raio, cor, nivel)
    if k not in _glows:
        s = pygame.Surface((2 * raio, 2 * raio))
        f = nivel / 5
        for i in range(raio, 0, -1):
            a = (1 - i / raio) ** 2 * f
            pygame.draw.circle(s, tuple(int(c * a) for c in cor), (raio, raio), i)
        _glows[k] = s
    return _glows[k]


def glow_rect(w, h, cor, nivel=5):
    k = (w, h, cor, nivel)
    if k not in _glows_r:
        _glows_r[k] = pygame.transform.smoothscale(glow(24, cor, nivel), (max(4, int(w * 2.0)), max(4, int(h * 2.0))))
    return _glows_r[k]


def _tmp(w, h):
    s = _tmps.get((w, h))
    if s is None:
        s = _tmps[(w, h)] = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    return s


def texto(f, s, cor):
    k = (id(f), s, cor)
    t = _txt.get(k)
    if t is None:
        if len(_txt) > 700:
            _txt.clear()
        t = _txt[k] = f.render(s, True, cor)
    return t


# ---------- fachadas ----------
def _produtos(s, J, icone, rng):
    prat = [J.y + J.h // 3, J.y + 2 * J.h // 3]
    for yy in prat:
        pygame.draw.line(s, (120, 90, 60), (J.x + 2, yy + 4), (J.right - 3, yy + 4), 2)
        x = J.x + 3
        while x < J.right - 6:
            if icone == "pao":
                pygame.draw.ellipse(s, rng.choice([(205, 140, 70), (225, 170, 95), (170, 100, 50)]), (x, yy - 2, 7, 5))
                x += 8
            elif icone == "cruz":
                pygame.draw.rect(s, rng.choice([(250, 250, 250), (60, 170, 120), (90, 140, 220)]), (x, yy - 3, 5, 7))
                x += 7
            else:
                pygame.draw.rect(s, rng.choice([(230, 80, 70), (250, 200, 60), (80, 170, 100), (240, 240, 240)]),
                                 (x, yy - 3, 5, 7))
                x += 7


def _icone(s, icone, cx, cy):
    if icone == "cruz":
        pygame.draw.rect(s, BRANCO, (cx - 1, cy - 5, 3, 11))
        pygame.draw.rect(s, BRANCO, (cx - 5, cy - 1, 11, 3))
    elif icone == "pao":
        pygame.draw.ellipse(s, (240, 190, 110), (cx - 6, cy - 3, 13, 7))
        pygame.draw.line(s, (170, 110, 50), (cx - 2, cy - 2), (cx - 1, cy + 2))
        pygame.draw.line(s, (170, 110, 50), (cx + 2, cy - 2), (cx + 3, cy + 2))
    else:
        pygame.draw.polygon(s, BRANCO, [(cx - 6, cy - 2), (cx + 6, cy - 2), (cx + 4, cy + 4), (cx - 4, cy + 4)])
        pygame.draw.line(s, BRANCO, (cx - 6, cy - 2), (cx - 8, cy - 5), 2)
        pygame.draw.circle(s, (60, 60, 60), (cx - 3, cy + 6), 1)
        pygame.draw.circle(s, (60, 60, 60), (cx + 3, cy + 6), 1)


def desenhar_loja(s, R, nome, tema, claro, icone, fonte, janelas):
    rng = random.Random(len(nome) * 97)
    sombra(s, R, 6, 8, 80, 3)
    gradiente_v(s, R, claro, tom(claro, .86))
    pygame.draw.rect(s, tom(claro, .55), R, 2, border_radius=3)
    L = pygame.Rect(R.x, R.y, R.w, 17)
    pygame.draw.rect(s, tema, L, border_radius=3)
    pygame.draw.rect(s, tom(tema, 1.4), L.inflate(-4, -4), 1, border_radius=2)
    _icone(s, icone, L.x + 13, L.centery)
    t = fonte.render(nome.upper(), True, BRANCO)
    s.blit(t, t.get_rect(center=(L.centerx + 8, L.centery)))
    ty = R.y + 17
    n = max(4, R.w // 10)
    for i in range(n):
        x0, x1 = R.x + R.w * i // n, R.x + R.w * (i + 1) // n
        cor = tema if i % 2 == 0 else (250, 248, 240)
        pygame.draw.rect(s, cor, (x0, ty, x1 - x0, 9))
        pygame.draw.circle(s, cor, ((x0 + x1) // 2, ty + 9), max(2, (x1 - x0) // 2))
    sh = pygame.Surface((R.w - 2, 6), pygame.SRCALPHA)
    sh.fill((0, 0, 0, 50))
    s.blit(sh, (R.x + 1, ty + 14))
    y0 = R.y + 32
    pw = 20
    porta = pygame.Rect(R.centerx - pw // 2, y0 - 1, pw, 27)
    jw = (R.w - pw - 24) // 2
    for J in (pygame.Rect(R.x + 8, y0, jw, 24), pygame.Rect(R.right - 8 - jw, y0, jw, 24)):
        pygame.draw.rect(s, (245, 245, 245), J.inflate(4, 4), border_radius=2)
        gradiente_v(s, J, (176, 216, 238), (108, 150, 190))
        _produtos(s, J, icone, rng)
        pygame.draw.line(s, (235, 248, 255), (J.x + 3, J.bottom - 3), (J.x + 9, J.y + 2), 1)
        pygame.draw.rect(s, (70, 76, 86), J, 1)
        janelas.append((J.centerx, J.centery, J.w, J.h))
    pygame.draw.rect(s, (60, 52, 48), porta.inflate(4, 2), border_radius=3)
    gradiente_v(s, porta.inflate(-4, -4), (170, 212, 232), (110, 150, 180))
    pygame.draw.line(s, (60, 52, 48), (porta.centerx, porta.y + 2), (porta.centerx, porta.bottom - 2))
    pygame.draw.rect(s, (232, 200, 90), (porta.centerx - 3, porta.centery, 2, 5))
    pygame.draw.rect(s, (232, 200, 90), (porta.centerx + 2, porta.centery, 2, 5))
    pygame.draw.rect(s, (220, 60, 60), (porta.x + 3, porta.y + 4, 8, 4), border_radius=1)
    janelas.append((porta.centerx, porta.centery, porta.w, porta.h))
    pygame.draw.rect(s, (112, 112, 120), (R.x + 1, R.bottom - 7, R.w - 2, 6))
    pygame.draw.rect(s, (132, 80, 50), (porta.x - 14, R.bottom - 11, 9, 7), border_radius=2)
    pygame.draw.circle(s, (46, 140, 62), (porta.x - 9, R.bottom - 14), 5)
    pygame.draw.rect(s, (132, 80, 50), (porta.right + 5, R.bottom - 11, 9, 7), border_radius=2)
    pygame.draw.circle(s, (56, 156, 70), (porta.right + 10, R.bottom - 14), 5)
    pygame.draw.circle(s, (240, 120, 150), (porta.right + 11, R.bottom - 16), 1)


def desenhar_casa(s, R, parede, telhado, seed=0):
    rng = random.Random(seed)
    th = int(R.h * 0.44)
    sombra(s, R, 5, 7, 75, 3)
    W = pygame.Rect(R.x, R.y + th - 2, R.w, R.h - th + 2)
    gradiente_v(s, W, parede, tom(parede, .84))
    pygame.draw.rect(s, tom(parede, .55), W, 1)
    pts = [(R.x - 3, R.y + th), (R.x + 9, R.y), (R.right - 9, R.y), (R.right + 3, R.y + th)]
    pygame.draw.polygon(s, telhado, pts)
    for yy in range(R.y + 3, R.y + th, 4):
        k = (yy - R.y) / th
        pygame.draw.line(s, tom(telhado, .78), (int(lerp(R.x + 9, R.x - 3, k)), yy), (int(lerp(R.right - 9, R.right + 3, k)), yy))
    pygame.draw.line(s, tom(telhado, 1.3), (R.x + 9, R.y + 1), (R.right - 9, R.y + 1), 2)
    pygame.draw.rect(s, (150, 84, 70), (R.right - 24, R.y - 3, 8, 11))
    pygame.draw.rect(s, (96, 90, 90), (R.right - 25, R.y - 4, 10, 3))
    bs = pygame.Surface((R.w, 4), pygame.SRCALPHA)
    bs.fill((0, 0, 0, 60))
    s.blit(bs, (R.x, R.y + th))
    ww, wh = 14, max(9, int(W.h * 0.38))
    janelas = []
    for wx in (R.x + 8, R.right - 8 - ww):
        J = pygame.Rect(wx, W.y + 6, ww, wh)
        pygame.draw.rect(s, tom(telhado, .9), J.inflate(8, 0))
        pygame.draw.rect(s, (250, 250, 250), J.inflate(2, 2))
        gradiente_v(s, J, (160, 205, 235), (96, 138, 178))
        pygame.draw.line(s, (250, 250, 250), (J.centerx, J.y), (J.centerx, J.bottom))
        pygame.draw.line(s, (250, 250, 250), (J.x, J.centery), (J.right, J.centery))
        pygame.draw.rect(s, (130, 80, 50), (J.x - 1, J.bottom + 1, J.w + 2, 3))
        for fx in range(J.x + 1, J.right, 3):
            pygame.draw.circle(s, rng.choice([(240, 90, 110), (250, 210, 70), (250, 250, 250)]), (fx, J.bottom), 1)
        janelas.append((J.centerx, J.centery, J.w, J.h))
    dh = W.h - 8
    porta = pygame.Rect(R.centerx - 7, W.bottom - dh, 14, dh)
    pygame.draw.rect(s, (84, 54, 36), porta.inflate(2, 0))
    pygame.draw.rect(s, (130, 84, 54), porta)
    pygame.draw.rect(s, (170, 212, 232), (porta.x + 3, porta.y + 3, 8, 5))
    pygame.draw.circle(s, (240, 210, 100), (porta.right - 3, porta.centery + 2), 1)
    pygame.draw.rect(s, (200, 200, 205), (porta.x - 2, W.bottom - 2, porta.w + 4, 3))
    pygame.draw.circle(s, (255, 226, 140), (porta.right + 5, porta.y + 3), 2)
    janelas.append((porta.right + 5, porta.y + 3, 6, 6))
    return janelas


# ---------- sprites de obstáculos ----------
PAD = 12
JAN_CASA = []


def sprite_obstaculo(o):
    r, tp, nome = o["rect"], o["tipo"], o["nome"]
    chave = (nome, tp, r.w, r.h)
    if chave in _sprites:
        return _sprites[chave]
    w, h = r.w, r.h
    s = pygame.Surface((w + 2 * PAD, h + 2 * PAD), pygame.SRCALPHA)
    R = pygame.Rect(PAD, PAD, w, h)
    rng = random.Random(w * 131 + h * 17 + len(nome))
    if nome == "Banca":
        sombra(s, R, 6, 8, 80, 4)
        pygame.draw.rect(s, (120, 78, 45), R, border_radius=4)
        roof = R.inflate(-4, -4)
        n = 7
        for i in range(n):
            y0, y1 = roof.y + i * roof.h // n, roof.y + (i + 1) * roof.h // n
            pygame.draw.rect(s, (205, 60, 55) if i % 2 == 0 else (245, 240, 230), (roof.x, y0, roof.w, y1 - y0))
        pygame.draw.line(s, (90, 40, 30), (roof.centerx, roof.y), (roof.centerx, roof.bottom), 2)
        pygame.draw.rect(s, (240, 224, 200), R, 2, border_radius=4)
        for i in range(4):
            pygame.draw.rect(s, rng.choice([(80, 140, 220), (240, 190, 60), (90, 180, 120)]),
                             (R.right - 8, R.y + 8 + i * 14, 6, 9))
    elif nome == "Copa de árvore":
        sombra(s, R.inflate(-6, -4), 11, 13, 75, elipse=True)
        base = R.inflate(-4, -2)
        pygame.draw.ellipse(s, (28, 92, 46), base)
        paleta = [(34, 112, 56), (46, 134, 66), (62, 152, 80), (82, 170, 96)]
        for _ in range(26):
            a, rr = rng.uniform(0, 6.283), rng.uniform(0, 0.78)
            cx = int(base.centerx + math.cos(a) * rr * base.w / 2)
            cy = int(base.centery + math.sin(a) * rr * base.h / 2)
            pygame.draw.circle(s, rng.choice(paleta), (cx, cy), rng.randint(8, 14))
        for _ in range(12):
            cx = int(base.centerx - base.w * 0.18 + rng.uniform(-14, 14))
            cy = int(base.centery - base.h * 0.2 + rng.uniform(-10, 10))
            pygame.draw.circle(s, (118, 196, 120), (cx, cy), rng.randint(3, 6))
    elif nome == "Poste":
        sombra(s, R, 5, 7, 80, elipse=True)
        c = R.center
        pygame.draw.circle(s, (62, 66, 74), c, 13)
        pygame.draw.circle(s, (150, 156, 166), c, 11, 2)
        pygame.draw.circle(s, (96, 102, 112), c, 7)
        pygame.draw.circle(s, (170, 176, 186), (c[0] - 2, c[1] - 2), 3)
        for a in range(0, 360, 90):
            pygame.draw.circle(s, (210, 214, 220), (int(c[0] + math.cos(math.radians(a + 45)) * 9),
                                                    int(c[1] + math.sin(math.radians(a + 45)) * 9)), 1)
    elif nome == "Caçamba U":
        sombra(s, R, 5, 6, 85, 3)
        pygame.draw.rect(s, (40, 98, 62), R, border_radius=3)
        pygame.draw.rect(s, (78, 152, 100), R.inflate(-4, -4), border_radius=2)
        longo = w >= h
        for k in range(10, (w if longo else h) - 4, 10):
            if longo:
                pygame.draw.line(s, (40, 98, 62), (R.x + k, R.y + 2), (R.x + k, R.bottom - 3))
            else:
                pygame.draw.line(s, (40, 98, 62), (R.x + 2, R.y + k), (R.right - 3, R.y + k))
        pygame.draw.rect(s, (230, 200, 40), (R.x, R.y, 6, 6))
        pygame.draw.rect(s, (230, 200, 40), (R.right - 6, R.bottom - 6, 6, 6))
        pygame.draw.rect(s, (24, 60, 40), R, 1, border_radius=3)
    elif nome == "Lixeira":
        sombra(s, R, 5, 6, 80, elipse=True)
        c = R.center
        pygame.draw.circle(s, (54, 62, 72), c, 18)
        pygame.draw.circle(s, (88, 112, 96), c, 15)
        pygame.draw.circle(s, (116, 142, 122), c, 11)
        pygame.draw.circle(s, (150, 176, 156), (c[0] - 3, c[1] - 3), 4)
        pygame.draw.line(s, (40, 46, 54), (c[0] - 5, c[1] + 2), (c[0] + 5, c[1] + 2), 3)
    elif nome == "Toldo":
        sombra(s, R, 13, 17, 55, 10)
        n = 9
        for i in range(n):
            x0, x1 = R.x + w * i // n, R.x + w * (i + 1) // n
            pygame.draw.rect(s, (60, 170, 160) if i % 2 == 0 else (250, 250, 245), (x0, R.y, x1 - x0, h - 6))
            pygame.draw.circle(s, (60, 170, 160) if i % 2 == 0 else (250, 250, 245), ((x0 + x1) // 2, R.bottom - 6),
                               max(2, (x1 - x0) // 2))
        pygame.draw.rect(s, (40, 110, 104), R.inflate(0, -4).move(0, -2), 2, border_radius=3)
        pygame.draw.line(s, (255, 255, 255), (R.x + 4, R.y + 4), (R.right - 4, R.y + 4), 1)
    elif nome == "Casa":
        JAN_CASA.clear()
        for jx, jy, jw, jh in desenhar_casa(s, R, (236, 206, 150), (170, 64, 54), 5):
            JAN_CASA.append((jx - PAD, jy - PAD, jw, jh))
    elif nome == "Prédio":
        sombra(s, R, 6, 8, 85, 3)
        pygame.draw.rect(s, (112, 118, 128), R, border_radius=3)
        pygame.draw.rect(s, (176, 180, 190), R, 3, border_radius=3)
        pygame.draw.rect(s, (96, 102, 112), R.inflate(-10, -10), border_radius=2)
        for i in range(3):
            ac = pygame.Rect(R.x + 10 + i * 22, R.y + 9, 16, 12)
            pygame.draw.rect(s, (190, 194, 202), ac, border_radius=2)
            pygame.draw.circle(s, (70, 76, 86), ac.center, 4)
        pygame.draw.rect(s, (110, 170, 214), (R.right - 22, R.bottom - 14, 14, 7))
    elif tp == "suspenso":
        sombra(s, R.inflate(-6, -6), 9, 11, 65, elipse=True)
        c = R.center
        c1, c2 = rng.choice([((230, 80, 70), (250, 240, 230)), ((70, 140, 220), (250, 240, 230)),
                             ((240, 180, 50), (250, 240, 230))])
        for k in range(8):
            a0, a1 = k * math.pi / 4, (k + 1) * math.pi / 4
            pts = [c] + [(c[0] + math.cos(a0 + (a1 - a0) * j / 4) * 21, c[1] + math.sin(a0 + (a1 - a0) * j / 4) * 21)
                         for j in range(5)]
            pygame.draw.polygon(s, c1 if k % 2 == 0 else c2, pts)
        pygame.draw.circle(s, (90, 90, 96), c, 3)
    else:
        sombra(s, R, 5, 6, 80, 3)
        pygame.draw.rect(s, (176, 124, 70), R, border_radius=3)
        for k in range(1, 4):
            pygame.draw.line(s, (136, 90, 48), (R.x + 2, R.y + k * h // 4), (R.right - 3, R.y + k * h // 4))
        pygame.draw.line(s, (120, 78, 40), (R.x + 3, R.y + 3), (R.right - 4, R.bottom - 4), 3)
        pygame.draw.line(s, (120, 78, 40), (R.right - 4, R.y + 3), (R.x + 3, R.bottom - 4), 3)
        pygame.draw.rect(s, (86, 54, 30), R, 2, border_radius=3)
        pygame.draw.rect(s, (255, 196, 40), (R.x + 2, R.y + 2, 8, 8))
        pygame.draw.polygon(s, (30, 30, 30), [(R.x + 2, R.y + 10), (R.x + 10, R.y + 2), (R.x + 10, R.y + 6), (R.x + 6, R.y + 10)])
    _sprites[chave] = s
    return s


def sprite_carro(cor, direcao, infrator):
    chave = ("carro", cor, direcao, infrator)
    if chave in _sprites:
        return _sprites[chave]
    s = pygame.Surface((56 + 2 * 10, 28 + 2 * 10), pygame.SRCALPHA)
    R = pygame.Rect(10, 10, 56, 28)
    sombra(s, R, 4, 6, 85, 8)
    for wx in (R.x + 8, R.x + 38):
        pygame.draw.rect(s, (18, 18, 22), (wx, R.y - 2, 12, 5), border_radius=2)
        pygame.draw.rect(s, (18, 18, 22), (wx, R.bottom - 3, 12, 5), border_radius=2)
    c = (230, 110, 40) if infrator else cor
    pygame.draw.rect(s, tom(c, .72), R, border_radius=8)
    pygame.draw.rect(s, c, R.inflate(0, -4), border_radius=8)
    pygame.draw.rect(s, tom(c, 1.2), (R.x + 4, R.y + 3, R.w - 8, 3), border_radius=2)
    cab = pygame.Rect(R.x + 14, R.y + 4, 26, 20)
    pygame.draw.rect(s, (36, 46, 64), cab, border_radius=5)
    pygame.draw.polygon(s, (60, 84, 112), [(cab.right - 1, cab.y + 2), (cab.right + 6, cab.y + 5),
                                           (cab.right + 6, cab.bottom - 5), (cab.right - 1, cab.bottom - 2)])
    pygame.draw.rect(s, tom(c, 1.12), (cab.x + 4, cab.y + 3, 16, 14), border_radius=3)
    pygame.draw.line(s, (130, 160, 200), (cab.x + 3, cab.y + 2), (cab.x + 3, cab.bottom - 3), 1)
    if infrator:
        pygame.draw.rect(s, (20, 20, 24), (R.x + 12, R.centery - 1, 30, 2))
    pygame.draw.rect(s, (255, 244, 190), (R.right - 4, R.y + 3, 4, 6), border_radius=1)
    pygame.draw.rect(s, (255, 244, 190), (R.right - 4, R.bottom - 9, 4, 6), border_radius=1)
    pygame.draw.rect(s, (170, 30, 36), (R.x, R.y + 3, 3, 6), border_radius=1)
    pygame.draw.rect(s, (170, 30, 36), (R.x, R.bottom - 9, 3, 6), border_radius=1)
    pygame.draw.circle(s, tom(c, .7), (R.x + 38, R.y - 1), 2)
    pygame.draw.circle(s, tom(c, .7), (R.x + 38, R.bottom), 2)
    pygame.draw.rect(s, (20, 22, 28), R, 1, border_radius=8)
    if direcao < 0:
        s = pygame.transform.flip(s, True, False)
    _sprites[chave] = s
    return s


def figura_pessoa(x, y, ang, fase, roupa, calca, cabelo, pele, acess=None, colete=False, tela=None):
    S, E = 30, 3
    big = _tmp(S * E, S * E)
    cx = cy = S * E // 2
    c, sn = math.cos(ang), math.sin(ang)

    def P(dx, dy):
        return (int(cx + (dx * c - dy * sn) * E), int(cy + (dx * sn + dy * c) * E))

    sw = math.sin(fase)
    for lado, sg in ((-1, 1), (1, -1)):
        pygame.draw.circle(big, (36, 36, 44), P(sw * sg * 4.2, lado * 3.0), int(2.6 * E))
    for lado, sg in ((-1, -1), (1, 1)):
        ombro, mao = P(0, lado * 5.5), P(sw * sg * 3.4 + 1, lado * 7.6)
        pygame.draw.line(big, roupa, ombro, mao, int(3.0 * E))
        pygame.draw.circle(big, pele, mao, int(1.9 * E))
    if acess == "mochila":
        pygame.draw.polygon(big, tom(roupa, .6), [P(-8, -4), P(-4, -4.5), P(-4, 4.5), P(-8, 4)])
    pts = [P(4.4 * math.cos(2 * math.pi * k / 16), 7.4 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    pygame.draw.polygon(big, roupa, pts)
    pygame.draw.polygon(big, tom(roupa, .65), pts, max(1, E // 2))
    if colete:
        pts2 = [P(3.4 * math.cos(2 * math.pi * k / 16), 6.2 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
        pygame.draw.polygon(big, (255, 150, 30), pts2)
        pygame.draw.line(big, (240, 240, 200), P(-1.5, -5.5), P(-1.5, 5.5), E)
        pygame.draw.line(big, (240, 240, 200), P(1.5, -5.5), P(1.5, 5.5), E)
    pygame.draw.circle(big, pele, P(0.6, 0), int(4.4 * E))
    pygame.draw.circle(big, cabelo, P(-0.9, 0), int(4.2 * E))
    if acess == "chapeu":
        pygame.draw.circle(big, (200, 170, 90), P(0, 0), int(6.2 * E))
        pygame.draw.circle(big, (150, 120, 60), P(0, 0), int(3.4 * E))
    small = pygame.transform.smoothscale(big, (S, S))
    (tela).blit(small, (int(x - S / 2), int(y - S / 2)))


def figura_robo(tela, x, y, ang, passo, pulso):
    S, E = 80, 2
    big = _tmp(S * E, S * E)
    cx = cy = S * E // 2
    c, sn = math.cos(ang), math.sin(ang)

    def P(dx, dy):
        return (int(cx + (dx * c - dy * sn) * E), int(cy + (dx * sn + dy * c) * E))

    b = math.sin(passo) * 5
    for ox, oy, f in [(11, -12, b), (11, 12, -b), (-12, -12, -b), (-12, 12, b)]:
        pygame.draw.circle(big, (10, 48, 86), P(ox + f, oy), int(5.6 * E))
        pygame.draw.circle(big, AZUL_ESC, P(ox + f, oy), int(4.6 * E))
        pygame.draw.circle(big, (60, 120, 180), P(ox + f + 1, oy), int(2.2 * E))
    pygame.draw.line(big, (40, 60, 90), P(-18, 0), P(-25, math.sin(pulso * 5) * 2), int(1.6 * E))
    pygame.draw.circle(big, (255, 80, 80) if int(pulso * 3) % 2 == 0 else (120, 40, 40), P(-25, math.sin(pulso * 5) * 2), int(1.8 * E))
    corpo = [P(-19, -8), P(-15, -11), P(12, -11), P(17, -7), P(17, 7), P(12, 11), P(-15, 11), P(-19, 8)]
    pygame.draw.polygon(big, AZUL, corpo)
    pygame.draw.polygon(big, (92, 176, 245), [P(-15, -8), P(12, -8), P(14, -5), P(-17, -5)])
    pygame.draw.polygon(big, BRANCO, corpo, int(1.6 * E))
    pygame.draw.polygon(big, LARANJA, [P(-1, -11), P(4, -11), P(4, 11), P(-1, 11)])
    pygame.draw.circle(big, (255, 190, 90), P(-9, 0), int(2.4 * E), max(1, E - 1))
    cab = P(21, 0)
    pygame.draw.polygon(big, AZUL_ESC, [P(15, -8), P(19, -14), P(22, -9)])
    pygame.draw.polygon(big, AZUL_ESC, [P(15, 8), P(19, 14), P(22, 9)])
    pygame.draw.circle(big, CABECA, cab, int(9.4 * E))
    pygame.draw.circle(big, AZUL_ESC, cab, int(9.4 * E), max(1, E))
    pygame.draw.ellipse(big, (24, 40, 64), pygame.Rect(0, 0, int(7 * E), int(11 * E)).move(P(21.5, 0)[0] - int(3.5 * E), P(21.5, 0)[1] - int(5.5 * E))) if abs(sn) < 0.01 and c > 0 else None
    for oy in (-3.2, 3.2):
        pygame.draw.circle(big, (90, 230, 255), P(27, oy), int(1.8 * E))
    pygame.draw.circle(big, (30, 30, 36), P(29.5, 0), int(2.0 * E))
    dome = P(3, 0)
    pygame.draw.circle(big, (230, 120, 20), dome, int(5.2 * E))
    pygame.draw.circle(big, (255, 190, 90), dome, int(5.2 * E), max(1, E - 1))
    a = pulso * 6
    pygame.draw.line(big, BRANCO, dome, (int(dome[0] + math.cos(a) * 4.4 * E), int(dome[1] + math.sin(a) * 4.4 * E)), max(1, E - 1))
    small = pygame.transform.smoothscale(big, (S, S))
    tela.blit(small, (int(x - S / 2), int(y - S / 2)))


# ---------- fundo estático ----------
def construir_fundo(fonte):
    rng = random.Random(11)
    s = pygame.Surface((AREA_W, ALTURA))
    s.fill((106, 110, 118))
    T = 26
    for ty in range(0, ALTURA, T):
        for tx in range(0, AREA_W, T):
            v = rng.randint(-6, 6)
            c = (CALCADA[0] + v, CALCADA[1] + v, CALCADA[2] + v + 2)
            pygame.draw.rect(s, c, (tx, ty, T - 1, T - 1))
            pygame.draw.line(s, tom(c, 1.09), (tx, ty), (tx + T - 2, ty))
    # grama
    for y0, y1 in ((0, 28), (ALTURA - 28, ALTURA)):
        pygame.draw.rect(s, GRAMA, (0, y0, AREA_W, y1 - y0))
        for _ in range(320):
            x, y = rng.randint(0, AREA_W), rng.randint(y0, y1 - 1)
            pygame.draw.line(s, tom(GRAMA, rng.uniform(.75, 1.3)), (x, y), (x + rng.randint(-1, 1), y - rng.randint(2, 4)))
        for _ in range(16):
            pygame.draw.circle(s, rng.choice([(250, 250, 250), (255, 220, 80), (250, 150, 190)]),
                               (rng.randint(4, AREA_W - 4), rng.randint(y0 + 3, y1 - 3)), 1)
    for x in range(20, AREA_W - 10, 34):
        pygame.draw.circle(s, (30, 90, 48), (x, 15), rng.randint(8, 11))
        pygame.draw.circle(s, (54, 140, 72), (x - 2, 13), rng.randint(5, 7))
    pygame.draw.line(s, (30, 80, 46), (0, 27), (AREA_W, 27), 2)
    pygame.draw.line(s, MEIO_FIO, (0, 29), (AREA_W, 29), 3)
    # rua
    pygame.draw.rect(s, ASFALTO, (0, RUA_Y, AREA_W, RUA_H))
    for _ in range(1900):
        x, y = rng.randint(0, AREA_W - 1), rng.randint(RUA_Y, RUA_Y + RUA_H - 1)
        v = rng.randint(-8, 8)
        s.set_at((x, y), (ASFALTO[0] + v, ASFALTO[1] + v, ASFALTO[2] + v))
    trilho = pygame.Surface((AREA_W, 9), pygame.SRCALPHA)
    trilho.fill((0, 0, 0, 24))
    for cy in (RUA_Y + 42, RUA_Y + 128):
        s.blit(trilho, (0, cy - 13))
        s.blit(trilho, (0, cy + 4))
    for _ in range(7):
        x, y = rng.randint(20, AREA_W - 60), rng.randint(RUA_Y + 12, RUA_Y + RUA_H - 12)
        pts = [(x, y)]
        for _ in range(4):
            x += rng.randint(6, 16)
            y += rng.randint(-5, 5)
            pts.append((x, y))
        pygame.draw.lines(s, (30, 32, 38), False, pts, 1)
    for yy in (RUA_Y + 9, RUA_Y + RUA_H - 10):
        pygame.draw.line(s, (150, 152, 158), (0, yy), (AREA_W, yy), 2)
    for x in range(15, AREA_W - 20, 45):
        if not (FAIXA_X - 20 <= x <= FAIXA_X + FAIXA_W):
            pygame.draw.line(s, BRANCO, (x, RUA_Y + RUA_H // 2), (x + 22, RUA_Y + RUA_H // 2), 3)
    # meio-fio
    pygame.draw.rect(s, (182, 186, 194), (0, RUA_Y - 6, AREA_W, 6))
    pygame.draw.line(s, (214, 218, 224), (0, RUA_Y - 6), (AREA_W, RUA_Y - 6), 1)
    pygame.draw.line(s, (56, 58, 66), (0, RUA_Y), (AREA_W, RUA_Y), 2)
    pygame.draw.rect(s, (182, 186, 194), (0, RUA_Y + RUA_H, AREA_W, 6))
    pygame.draw.line(s, (214, 218, 224), (0, RUA_Y + RUA_H + 5), (AREA_W, RUA_Y + RUA_H + 5), 1)
    pygame.draw.line(s, (56, 58, 66), (0, RUA_Y + RUA_H - 1), (AREA_W, RUA_Y + RUA_H - 1), 2)
    # faixa de pedestres + linhas de retenção
    for y in range(RUA_Y + 12, RUA_Y + RUA_H - 12, 22):
        pygame.draw.rect(s, (238, 238, 234), (FAIXA_X, y, FAIXA_W, 12))
        for _ in range(26):
            s.set_at((rng.randint(FAIXA_X, FAIXA_X + FAIXA_W - 1), rng.randint(y, y + 11)), (170, 170, 168))
    pygame.draw.rect(s, (238, 238, 234), (LINHA_E - 3, RUA_Y + 5, 5, RUA_H // 2 - 8))
    pygame.draw.rect(s, (238, 238, 234), (LINHA_W - 2, RUA_Y + RUA_H // 2 + 4, 5, RUA_H // 2 - 9))
    # piso tátil + rampas
    def tatil(r):
        pygame.draw.rect(s, (190, 146, 14), r.inflate(2, 2))
        pygame.draw.rect(s, PISO_TATIL, r)
        for xx in range(r.x + 1, r.right - 1, 3):
            for yy in range(r.y + 1, r.bottom - 1, 3):
                pygame.draw.rect(s, (255, 236, 130), (xx, yy, 2, 2))
    for t in TATIL:
        tatil(t)
    tatil(pygame.Rect(FAIXA_X + 12, RUA_Y - 6, FAIXA_W - 24, 6))
    tatil(pygame.Rect(FAIXA_X + 12, RUA_Y + RUA_H, FAIXA_W - 24, 6))
    # fachadas
    janelas = []
    for f in FACHADAS:
        if f["tipo"] == "loja":
            desenhar_loja(s, f["rect"], f["nome"], f["tema"], f["claro"], f["icone"], fonte, janelas)
        else:
            janelas += desenhar_casa(s, f["rect"], f["parede"], f["telhado"], f["rect"].x)
    # postes de luz
    for x, y, d in POSTES_LUZ:
        sombra(s, (x - 4, y - 4, 8, 8), 4, 5, 70, elipse=True)
        pygame.draw.line(s, (60, 64, 72), (x, y), (x, y + 11 * d), 3)
        pygame.draw.rect(s, (230, 224, 190), (x - 4, y + 9 * d - (0 if d > 0 else 4), 8, 5), border_radius=2)
        pygame.draw.circle(s, (46, 50, 58), (x, y), 5)
        pygame.draw.circle(s, (130, 136, 146), (x, y), 3)
    # vinheta
    mini = pygame.Surface((48, 41), pygame.SRCALPHA)
    for yy in range(41):
        for xx in range(48):
            d = math.hypot((xx - 23.5) / 24, (yy - 20) / 20.5)
            mini.set_at((xx, yy), (0, 0, 0, int(clamp((d - 0.62) / 0.55, 0, 1) ** 2 * 95)))
    s.blit(pygame.transform.smoothscale(mini, (AREA_W, ALTURA)), (0, 0))
    return s, janelas


# ==================== APLICATIVO / INTERFACE ====================
class App:
    def __init__(self, seed, hora="dia"):
        pygame.init()
        try:
            pygame.mixer.init(22050, -16, 2, 512)
        except pygame.error:
            pass
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption("DOG-IA V2 — Cão-Guia Autônomo (Arquitetura Híbrida)")
        self.clock = pygame.time.Clock()
        self.seed = seed
        self.m = Mundo(seed)
        self.t = 0.0
        self.pausa, self.grade_on, self.lidar_on = False, False, True
        self.preset = hora
        self.luz = [float(v) for v in PRESETS[hora]]
        self.toasts, self.ondas = [], []
        self.grade_surf = self.grade_id = None
        self.mouse, self.hover, self.cursor = (0, 0), None, None
        SF = pygame.font.SysFont
        self.f = dict(titulo=SF("arial", 20, True), h=SF("arial", 15, True), n=SF("arial", 13),
                      p=SF("arial", 12, True), t=SF("arial", 11), v=SF("arial", 15, True),
                      placa=SF("arial", 11, True), dig=SF("consolas,couriernew,arial", 14, True),
                      grande=SF("arial", 22, True))
        self.fundo, self.janelas = construir_fundo(self.f["placa"])
        self.fundo = self.fundo.convert()
        self.luz_surf = pygame.Surface((AREA_W, ALTURA))
        blob = pygame.Surface((80, 40), pygame.SRCALPHA)
        for ex, ey, ew, eh in ((4, 10, 44, 24), (24, 4, 40, 28), (40, 12, 36, 22), (14, 16, 50, 20)):
            pygame.draw.ellipse(blob, (0, 0, 20, 34), (ex, ey, ew, eh))
        self.nuvem = pygame.transform.smoothscale(blob, (320, 160)).convert_alpha()
        self.tmp_lidar = pygame.Surface((2 * ALC, 2 * ALC), pygame.SRCALPHA)
        self._layout()
        self._botoes()

    # ---------- layout do painel ----------
    def _layout(self):
        self.px = AREA_W
        self.X0 = AREA_W + 12
        self.Y = dict(titulo=10, status=66, tiles=140, sem=342, dest=414, vis=500, ajuda=614)
        p = pygame.Surface((LARGURA - AREA_W, ALTURA))
        gradiente_v(p, p.get_rect(), (16, 18, 26), (24, 28, 40))
        pygame.draw.line(p, (60, 70, 96), (0, 0), (0, ALTURA), 2)
        def card(y, h):
            pygame.draw.rect(p, (32, 38, 54), (12, y, 236, h), border_radius=10)
            pygame.draw.rect(p, (54, 62, 86), (12, y, 236, h), 1, border_radius=10)
        card(self.Y["titulo"], 48)
        card(self.Y["status"], 66)
        for i in range(5):
            for j in range(2):
                pygame.draw.rect(p, (32, 38, 54), (12 + j * 122, self.Y["tiles"] + i * 40, 114, 34), border_radius=8)
        card(self.Y["sem"], 64)
        self.painel = p.convert()

    def _botoes(self):
        self.botoes = []

        def add(x, y, w, h, rot, acao, ativo=None):
            self.botoes.append(dict(rect=pygame.Rect(x, y, w, h), rot=rot, acao=acao, ativo=ativo))
        for i, (k, (nome, _)) in enumerate(DESTINOS.items()):
            add(self.X0 + (i % 2) * 122, self.Y["dest"] + 16 + (i // 2) * 34, 114, 28, f"{k}  {nome}",
                (lambda kk=k: self.m.iniciar_viagem(kk)),
                (lambda kk=k: self.m.dest == kk and self.m.estado != "OCIOSO"))
        yv = self.Y["vis"] + 16
        defs = [("Grade (G)", self.alt_grade, lambda: self.grade_on),
                ("LiDAR (L)", self.alt_lidar, lambda: self.lidar_on),
                (lambda: f"{ROTULO_HORA[self.preset]} (N)", self.alt_hora, lambda: self.preset != "dia"),
                (lambda: "Retomar (P)" if self.pausa else "Pausar (P)", self.alt_pausa, lambda: self.pausa),
                ("Reiniciar (R)", self.reiniciar, None),
                ("Limpar obst. (C)", self.limpar, None)]
        for i, (rot_, ac, at) in enumerate(defs):
            add(self.X0 + (i % 2) * 122, yv + (i // 2) * 32, 114, 26, rot_, ac, at)

    # ---------- ações ----------
    def alt_grade(self):
        self.grade_on = not self.grade_on

    def alt_lidar(self):
        self.lidar_on = not self.lidar_on

    def alt_pausa(self):
        self.pausa = not self.pausa

    def alt_hora(self):
        ordem = ["dia", "tarde", "noite"]
        self.preset = ordem[(ordem.index(self.preset) + 1) % 3]

    def reiniciar(self):
        self.m = Mundo(self.seed)
        self.toast("Simulação reiniciada")

    def limpar(self):
        antes = len(self.m.obstaculos)
        self.m.obstaculos = [o for o in self.m.obstaculos if o["nome"] != "Obstáculo"]
        if len(self.m.obstaculos) != antes:
            self.m.reconstruir_grade()
            self.toast("Obstáculos criados foram removidos")

    def toast(self, msg, cor=BRANCO):
        if msg:
            self.toasts.append([msg, 2.4, cor])
            del self.toasts[:-3]

    # ---------- eventos ----------
    def evento(self, e):
        if e.type == pygame.QUIT:
            return False
        if e.type == pygame.MOUSEMOTION:
            self.mouse = e.pos
        elif e.type == pygame.MOUSEBUTTONDOWN:
            if e.pos[0] >= AREA_W:
                if e.button == 1:
                    for b in self.botoes:
                        if b["rect"].collidepoint(e.pos):
                            b["acao"]()
            elif e.button == 1:
                self.toast(self.m.ir_para(*e.pos), LARANJA)
                self.ondas.append([e.pos[0], e.pos[1], 0.0])
            elif e.button == 3:
                self.toast(self.m.alternar_obstaculo(*e.pos))
        elif e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                self.m.iniciar_viagem(e.key - pygame.K_0)
            elif e.key in (pygame.K_KP1, pygame.K_KP2, pygame.K_KP3, pygame.K_KP4):
                self.m.iniciar_viagem(e.key - pygame.K_KP1 + 1)
            elif e.key == pygame.K_g:
                self.alt_grade()
            elif e.key in (pygame.K_p, pygame.K_SPACE):
                self.alt_pausa()
            elif e.key == pygame.K_r:
                self.reiniciar()
            elif e.key == pygame.K_l:
                self.alt_lidar()
            elif e.key == pygame.K_n:
                self.alt_hora()
            elif e.key == pygame.K_c:
                self.limpar()
            elif e.key == pygame.K_ESCAPE:
                return False
        return True

    def atualizar(self, dt):
        self.t += dt
        alvo = PRESETS[self.preset]
        for i in range(3):
            self.luz[i] += (alvo[i] - self.luz[i]) * min(1.0, dt * 2.2)
        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]
        for o in self.ondas:
            o[2] += dt
        self.ondas = [o for o in self.ondas if o[2] < 0.8]
        mx, my = self.mouse
        self.hover = self.m.obstaculo_em(mx, my) if mx < AREA_W else None
        try:
            if mx >= AREA_W and any(b["rect"].collidepoint(self.mouse) for b in self.botoes) or self.hover:
                novo = pygame.SYSTEM_CURSOR_HAND
            else:
                novo = pygame.SYSTEM_CURSOR_ARROW
            if novo != self.cursor:
                pygame.mouse.set_cursor(novo)
                self.cursor = novo
        except (pygame.error, AttributeError):
            pass
        if id(self.m.grade) != self.grade_id:
            self.grade_surf, self.grade_id = self.m.grade.superficie(), id(self.m.grade)

    # ---------- desenho do cenário ----------
    def desenhar_destinos(self):
        tela, m = self.tela, self.m
        for k, (nome, (x, y)) in DESTINOS.items():
            ativo = m.dest == k and m.estado != "OCIOSO"
            pulso = 2 * math.sin(self.t * 4 + k) if ativo else 0
            cor = VERDE if ativo else (255, 255, 255)
            pygame.draw.circle(tela, tom(cor, .5), (x, y), int(15 + pulso))
            pygame.draw.circle(tela, cor, (x, y), int(15 + pulso), 3)
            pygame.draw.line(tela, (60, 60, 66), (x - 3, y + 7), (x - 3, y - 8), 2)
            pygame.draw.polygon(tela, VERDE if ativo else LARANJA, [(x - 2, y - 8), (x + 8, y - 5), (x - 2, y - 2)])
            lbl = texto(self.f["placa"], f"{k} · {nome}", BRANCO)
            ly = y + 18 if y < RUA_Y else y - 34
            chip = pygame.Rect(0, 0, lbl.get_width() + 14, 17)
            chip.midtop = (x, ly)
            sombra(tela, chip, 2, 3, 70, 8)
            pygame.draw.rect(tela, (24, 28, 40), chip, border_radius=8)
            pygame.draw.rect(tela, cor if ativo else (90, 98, 120), chip, 1, border_radius=8)
            tela.blit(lbl, lbl.get_rect(center=chip.center))
        if m.dest is None and m.estado != "OCIOSO":
            x, y = int(m.alvo[0]), int(m.alvo[1])
            r = 10 + 3 * math.sin(self.t * 6)
            pygame.draw.circle(tela, LARANJA, (x, y), int(r), 2)
            pygame.draw.circle(tela, (255, 230, 160), (x, y), 3)
            pygame.draw.line(tela, (60, 60, 66), (x, y), (x, y - 18), 2)
            pygame.draw.polygon(tela, LARANJA, [(x, y - 18), (x + 11, y - 14), (x, y - 10)])

    def desenhar_rota(self):
        m, tela = self.m, self.tela
        if not m.caminho or m.estado == "OCIOSO":
            return
        pts = m.caminho[m.idx:]
        off = int(self.t * 12)
        for i in range(len(pts) - 1):
            if ((i + off) // 2) % 2 == 0:
                pygame.draw.line(tela, (0, 210, 255), pts[i], pts[i + 1], 3)

    def desenhar_semaforos(self):
        tela, sem = self.tela, self.m.sem
        n = sem.nome
        noite = min(self.luz) < 200
        for tipo, x, y, lado in SEMS:
            if tipo == "carro":
                on = 2 if n == "VERDE" else 1 if n == "AMARELO" else 0
                cores_on = (VERMELHO, AMARELO_S, VERDE)
                cores_off = ((70, 20, 20), (70, 60, 10), (20, 70, 40))
                h, ys = 52, (y + 10, y + 26, y + 42)
                val, cor = sem.cont_carro()
            else:
                on = 1 if n == "PEDESTRE" else 0
                if on and sem.restante < 3 and int(self.t * 4) % 2:
                    on = -1
                cores_on = (VERMELHO, VERDE)
                cores_off = ((70, 20, 20), (20, 70, 40))
                h, ys = 36, (y + 10, y + 26)
                val, cor = sem.cont_pedestre()
            sombra(tela, (x, y, 18, h), 4, 5, 65, 5)
            pygame.draw.rect(tela, (26, 28, 34), (x, y, 18, h), border_radius=5)
            pygame.draw.rect(tela, (78, 84, 98), (x, y, 18, h), 1, border_radius=5)
            for i, yy in enumerate(ys):
                lit = i == on
                pygame.draw.circle(tela, cores_on[i] if lit else cores_off[i], (x + 9, yy), 5)
                if lit:
                    tela.blit(glow(15, cores_on[i], 4 if noite else 3), (x + 9 - 15, yy - 15), special_flags=pygame.BLEND_RGB_ADD)
                    pygame.draw.circle(tela, (255, 255, 255), (x + 7, yy - 2), 1)
            if tipo == "pedestre" and on == -1:
                cor = (60, 90, 70)
            px_ = x - 36 if lado < 0 else x + 22
            pan = pygame.Rect(px_, y + (h - 18) // 2, 32, 18)
            sombra(tela, pan, 2, 3, 70, 5)
            pygame.draw.rect(tela, (12, 14, 18), pan, border_radius=5)
            pygame.draw.rect(tela, tom(cor, .8), pan, 1, border_radius=5)
            num = f"{max(0, math.ceil(val - 1e-6)):02d}"
            tt = texto(self.f["dig"], num, cor)
            tela.blit(tt, tt.get_rect(center=pan.center))

    def desenhar_lidar(self):
        r = self.m.robo
        if not self.lidar_on or not r.filtrado:
            return
        lid = self.tmp_lidar
        lid.fill((0, 0, 0, 0))
        pts = [(ALC, ALC)]
        for ang, d, tipo in r.filtrado:
            pts.append((ALC + math.cos(ang) * d, ALC + math.sin(ang) * d))
        pygame.draw.polygon(lid, (0, 200, 255, 34), pts)
        for ang, d, tipo in r.filtrado:
            fim = (ALC + math.cos(ang) * d, ALC + math.sin(ang) * d)
            livre = d >= ALC - 5
            pygame.draw.line(lid, (46, 204, 113, 130) if livre else (255, 70, 70, 190), (ALC, ALC), fim, 1)
            if tipo:
                pygame.draw.circle(lid, (255, 255, 255, 230), (int(fim[0]), int(fim[1])), 3)
        self.tela.blit(lid, (int(r.x - ALC), int(r.y - ALC)))

    def desenhar_agentes(self):
        tela, m, t = self.tela, self.m, self.t
        r, tu = m.robo, m.tutor
        sh = _sprites.get("sombra_p")
        if sh is None:
            sh = pygame.Surface((20, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
            _sprites["sombra_p"] = sh
        shr = _sprites.get("sombra_r")
        if shr is None:
            shr = pygame.Surface((44, 26), pygame.SRCALPHA)
            pygame.draw.ellipse(shr, (0, 0, 0, 80), shr.get_rect())
            _sprites["sombra_r"] = shr
        for p in m.pedestres:
            tela.blit(sh, (int(p.x - 7), int(p.y - 1)))
        tela.blit(sh, (int(tu.x - 7), int(tu.y)))
        tela.blit(shr, (int(r.x - 18), int(r.y - 6)))
        for v in m.veiculos:
            sp = sprite_carro(v.cor, v.dir, v.infrator)
            tela.blit(sp, (int(v.x) - 38, int(v.y) - 24))
            traseira = int(v.x - v.dir * 28)
            if v.a < -25:
                pygame.draw.rect(tela, (255, 60, 60), (traseira - (0 if v.dir == 1 else 3), int(v.y) - 11, 3, 6))
                pygame.draw.rect(tela, (255, 60, 60), (traseira - (0 if v.dir == 1 else 3), int(v.y) + 5, 3, 6))
                tela.blit(glow(12, (255, 40, 40), 4), (traseira - 12, int(v.y) - 12), special_flags=pygame.BLEND_RGB_ADD)
            if v.infrator:
                a = int(t * 6) % 2
                pygame.draw.circle(tela, (255, 40, 40) if a else (40, 80, 255), (int(v.x) - 4, int(v.y)), 3)
                pygame.draw.circle(tela, (40, 80, 255) if a else (255, 40, 40), (int(v.x) + 4, int(v.y)), 3)
        for p in m.pedestres:
            figura_pessoa(p.x, p.y, p.ang, p.fase, p.cores[0], p.cores[1], p.cores[2], p.cores[3], p.acessorio, False, tela)
        # arnês
        tens = tu.tensao > 10
        folga = (255, 120, 60) if tens else DOURADO
        meio = ((r.x + tu.x) / 2, (r.y + tu.y) / 2 + (0 if tens else 3))
        pygame.draw.lines(tela, folga, False, [(r.x, r.y), meio, (tu.x, tu.y)], 3)
        figura_pessoa(tu.x, tu.y, math.atan2(r.y - tu.y, r.x - tu.x), r.passo * 0.7, (42, 52, 80), (30, 30, 40),
                      (30, 24, 20), (230, 190, 150), None, True, tela)
        self.desenhar_lidar()
        figura_robo(tela, r.x, r.y, r.angulo, r.passo, t)

    def desenhar_suspensos(self):
        for o in self.m.obstaculos:
            if o["tipo"] == "suspenso":
                sp = sprite_obstaculo(o)
                dx = math.sin(self.t * 1.3 + o["rect"].x * 0.05) * 1.4 if o["nome"] == "Copa de árvore" else 0
                self.tela.blit(sp, (o["rect"].x - PAD + int(dx), o["rect"].y - PAD))

    def aplicar_luz(self):
        amb = self.luz
        if min(amb) >= 252:
            return
        escuro = 1 - sum(amb) / 765
        nivel = int(clamp(round(escuro / 0.42 * 5), 0, 5))
        luz = self.luz_surf
        luz.fill((int(amb[0]), int(amb[1]), int(amb[2])))
        add = pygame.BLEND_RGB_ADD
        m = self.m
        if nivel > 0:
            quente = (255, 214, 140)
            for x, y, d in POSTES_LUZ:
                luz.blit(glow(80, quente, nivel), (x - 80, y + 10 * d - 80), special_flags=add)
            flick = 1.0
            for jx, jy, jw, jh in self.janelas:
                g = glow_rect(jw, jh, (255, 200, 110), nivel)
                luz.blit(g, (jx - g.get_width() // 2, jy - g.get_height() // 2), special_flags=add)
            for o in m.obstaculos:
                if o["nome"] == "Casa":
                    for jx, jy, jw, jh in JAN_CASA:
                        g = glow_rect(jw, jh, (255, 200, 110), nivel)
                        luz.blit(g, (o["rect"].x + jx - g.get_width() // 2, o["rect"].y + jy - g.get_height() // 2), special_flags=add)
            for v in m.veiculos:
                fx = int(v.x + v.dir * 66)
                luz.blit(glow(64, (255, 240, 190), nivel), (fx - 64, int(v.y) - 64), special_flags=add)
                luz.blit(glow(18, (255, 40, 40), nivel), (int(v.x - v.dir * 30) - 18, int(v.y) - 18), special_flags=add)
            sem = m.sem
            for tipo, x, y, lado in SEMS:
                if tipo == "carro":
                    cor = (VERDE, AMARELO_S, VERMELHO)[0 if sem.nome == "VERDE" else 1 if sem.nome == "AMARELO" else 2]
                else:
                    cor = VERDE if sem.nome == "PEDESTRE" else VERMELHO
                luz.blit(glow(34, cor, nivel), (x + 9 - 34, y + 24 - 34), special_flags=add)
            r = m.robo
            luz.blit(glow(46, (90, 220, 255), nivel), (int(r.x) - 46, int(r.y) - 46), special_flags=add)
            fx, fy = r.x + math.cos(r.angulo) * 40, r.y + math.sin(r.angulo) * 40
            luz.blit(glow(52, (255, 244, 210), nivel), (int(fx) - 52, int(fy) - 52), special_flags=add)
        self.tela.blit(luz, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def desenhar_nuvens(self):
        if min(self.luz) < 200:
            return
        for i in range(3):
            x = (self.t * (9 + i * 3) + i * 330) % (AREA_W + 640) - 320
            self.tela.blit(self.nuvem, (int(x), 40 + i * 210 + int(math.sin(self.t * 0.2 + i) * 20)))

    def desenhar_hud_mapa(self):
        tela, m = self.tela, self.m
        for x, y, t in self.ondas:
            k = t / 0.8
            r = int(6 + 30 * k)
            cor = mix(LARANJA, (60, 60, 70), k)
            pygame.draw.circle(tela, cor, (int(x), int(y)), r, 2)
        mx, my = self.mouse
        if mx < AREA_W:
            if self.hover:
                o = self.hover
                pygame.draw.rect(tela, (255, 170, 40), o["rect"].inflate(6, 6), 2, border_radius=6)
                linhas = [f"{o['nome']} · {o['tipo']}", "Fixo" if o.get("fixo") else "Botão direito: remover"]
                ws = [texto(self.f["t"], s_, BRANCO) for s_ in linhas]
                w, h = max(a.get_width() for a in ws) + 14, 36
                bx, by = clamp(mx + 14, 4, AREA_W - w - 4), clamp(my + 16, 4, ALTURA - h - 4)
                sombra(tela, (bx, by, w, h), 2, 3, 80, 7)
                pygame.draw.rect(tela, (24, 28, 40), (bx, by, w, h), border_radius=7)
                pygame.draw.rect(tela, (255, 170, 40), (bx, by, w, h), 1, border_radius=7)
                for i, a in enumerate(ws):
                    tela.blit(a, (bx + 7, by + 4 + i * 15))
            else:
                pygame.draw.circle(tela, (255, 255, 255), (mx, my), 9, 1)
                pygame.draw.circle(tela, (255, 255, 255), (mx, my), 2)
        for i, (msg, tm, cor) in enumerate(reversed(self.toasts)):
            tt = texto(self.f["p"], msg, BRANCO)
            w = tt.get_width() + 26
            rc = pygame.Rect(0, 0, w, 26)
            rc.midtop = (AREA_W // 2, 10 + i * 32)
            sombra(tela, rc, 2, 3, 80, 12)
            pygame.draw.rect(tela, (22, 26, 38), rc, border_radius=13)
            pygame.draw.rect(tela, cor if cor != BRANCO else (90, 100, 130), rc, 1, border_radius=13)
            tela.blit(tt, tt.get_rect(center=rc.center))
        if self.pausa:
            tt = texto(self.f["grande"], "PAUSADO", LARANJA)
            tela.blit(tt, (20, 44))

    # ---------- painel lateral ----------
    def desenhar_painel(self, fps):
        tela, m, F, X0, Y = self.tela, self.m, self.f, self.X0, self.Y
        tela.blit(self.painel, (self.px, 0))
        tela.blit(texto(F["titulo"], "DOG-IA V2", AZUL), (X0 + 12, Y["titulo"] + 6))
        tela.blit(texto(F["t"], "Cão-guia autônomo · híbrido", (140, 150, 175)), (X0 + 12, Y["titulo"] + 30))
        fp = texto(F["t"], f"{fps:3.0f} FPS", (110, 200, 140) if fps >= 50 else LARANJA)
        tela.blit(fp, (X0 + 224 - fp.get_width(), Y["titulo"] + 8))
        cores_est = {"FREIO_EMERGENCIA": VERMELHO, "AGUARDANDO_SINAL": LARANJA, "DESVIANDO": LARANJA,
                     "OCIOSO": (140, 150, 175), "CHEGOU": DOURADO}
        ce = cores_est.get(m.estado, VERDE)
        ys = Y["status"]
        pygame.draw.rect(tela, ce, (12 + self.px, ys + 8, 4, 50), border_radius=2)
        tela.blit(texto(F["h"], m.estado.replace("_", " "), ce), (X0 + 14, ys + 8))
        tela.blit(texto(F["t"], f"{m.rotulo} · {m.fase if m.rotulo != '-' else '-'}", (140, 150, 175)), (X0 + 14, ys + 27))
        palavras, linha, ya = STATUS[m.estado].split(" "), "", ys + 42
        for p in palavras:
            if F["t"].size(linha + p)[0] < 215:
                linha += p + " "
            else:
                tela.blit(texto(F["t"], linha, BRANCO), (X0 + 14, ya))
                ya, linha = ya + 13, p + " "
        if ya < ys + 62:
            tela.blit(texto(F["t"], linha, BRANCO), (X0 + 14, ya))
        tiles = [("TEMPO", f"{m.met['tempo']:.1f} s"), ("DISTÂNCIA", f"{m.met['dist']:.0f} px"),
                 ("TENSÃO ARNÊS", f"{m.tutor.tensao:.1f} px"), ("PAN ÁUDIO", f"{m.pan:+.2f}"),
                 ("VIAGENS", f"{m.met['viagens']}"), ("REPLANS", f"{m.replans}"),
                 ("ALERTAS", f"{m.met['alertas']}"), ("FREIOS", f"{m.met['freios']}"),
                 ("COLISÕES", f"{m.met['colisoes']}"), ("QUASE", f"{m.met['quase']}")]
        for i, (lab, val) in enumerate(tiles):
            x, y = X0 + (i % 2) * 122, Y["tiles"] + (i // 2) * 40
            cor = BRANCO
            if lab == "TENSÃO ARNÊS" and m.tutor.tensao > 10:
                cor = LARANJA
            if lab == "COLISÕES" and m.met["colisoes"]:
                cor = VERMELHO
            tela.blit(texto(F["t"], lab, (120, 130, 158)), (x + 9, y + 4))
            tela.blit(texto(F["v"], val, cor), (x + 9, y + 16))
        # semáforo
        sy = Y["sem"]
        sem = m.sem
        vc, cc = sem.cont_carro()
        vp, cp = sem.cont_pedestre()
        on = 2 if sem.nome == "VERDE" else 1 if sem.nome == "AMARELO" else 0
        for i, (c_on, c_off) in enumerate(((VERMELHO, (70, 24, 24)), (AMARELO_S, (70, 60, 14)), (VERDE, (22, 70, 40)))):
            pygame.draw.circle(tela, c_on if i == on else c_off, (X0 + 20 + i * 14, sy + 17), 5)
        tela.blit(texto(F["p"], "Carros", BRANCO), (X0 + 68, sy + 10))
        t1 = texto(F["v"], f"{max(0, math.ceil(vc - 1e-6)):02d}s", cc)
        tela.blit(t1, (X0 + 224 - t1.get_width(), sy + 9))
        ped = sem.nome == "PEDESTRE"
        pygame.draw.circle(tela, VERMELHO if not ped else (70, 24, 24), (X0 + 20, sy + 40), 5)
        pygame.draw.circle(tela, VERDE if ped else (22, 70, 40), (X0 + 34, sy + 40), 5)
        tela.blit(texto(F["p"], "Pedestres", BRANCO), (X0 + 68, sy + 33))
        t2 = texto(F["v"], f"{max(0, math.ceil(vp - 1e-6)):02d}s", cp)
        tela.blit(t2, (X0 + 224 - t2.get_width(), sy + 32))
        frac = clamp(sem.restante / FASES[sem.i][1], 0, 1)
        pygame.draw.rect(tela, (22, 26, 38), (X0 + 12, sy + 56, 212, 4), border_radius=2)
        pygame.draw.rect(tela, cc if on != 0 or sem.nome in ("TODOS_VERM_1", "TODOS_VERM_2") else cp,
                         (X0 + 12, sy + 56, int(212 * frac), 4), border_radius=2)
        tela.blit(texto(F["t"], f"Limite de travessia: {limite_travessia():.2f}s", (120, 130, 158)), (X0 + 12, sy + 44 + 22 - 22 + 0) if False else (X0 + 130, sy + 56 - 0) if False else (X0 + 100, sy + 56 - 0)) if False else None
        # botões
        tela.blit(texto(F["t"], "DESTINOS", (120, 130, 158)), (X0 + 2, Y["dest"]))
        tela.blit(texto(F["t"], "VISUAL E CONTROLES", (120, 130, 158)), (X0 + 2, Y["vis"]))
        for b in self.botoes:
            ativo = b["ativo"]() if b["ativo"] else False
            hov = b["rect"].collidepoint(self.mouse)
            cor = (30, 136, 229) if ativo else (62, 72, 100) if hov else (40, 47, 66)
            pygame.draw.rect(tela, cor, b["rect"], border_radius=8)
            pygame.draw.rect(tela, (96, 110, 150) if hov else (60, 70, 96), b["rect"], 1, border_radius=8)
            rot_ = b["rot"]() if callable(b["rot"]) else b["rot"]
            tt = texto(F["p"], rot_, BRANCO)
            tela.blit(tt, tt.get_rect(center=b["rect"].center))
        ajuda = ["Clique esq.: caminhar até o ponto", "Clique dir.: criar / remover obstáculo",
                 "Laranja c/ pisca: carro infrator", "1-4 destinos · G L N P R C"]
        for i, a in enumerate(ajuda):
            tela.blit(texto(F["t"], a, (150, 160, 185)), (X0 + 2, Y["ajuda"] + i * 15))

    # ---------- quadro completo ----------
    def desenhar(self, fps):
        tela, m = self.tela, self.m
        tela.blit(self.fundo, (0, 0))
        if self.grade_on:
            tela.blit(self.grade_surf, (0, 0))
        self.desenhar_destinos()
        self.desenhar_rota()
        for o in m.obstaculos:
            if o["tipo"] != "suspenso":
                tela.blit(sprite_obstaculo(o), (o["rect"].x - PAD, o["rect"].y - PAD))
        self.desenhar_agentes()
        self.desenhar_suspensos()
        self.desenhar_semaforos()
        self.desenhar_nuvens()
        self.aplicar_luz()
        self.desenhar_hud_mapa()
        self.desenhar_painel(fps)

    def rodar(self):
        rodando = True
        while rodando:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for e in pygame.event.get():
                if not self.evento(e):
                    rodando = False
            if not self.pausa:
                self.m.passo(dt)
            self.atualizar(dt)
            if self.m.bip:
                tocar_bip(*self.m.bip)
                self.m.bip = None
            self.desenhar(self.clock.get_fps())
            pygame.display.flip()
        pygame.quit()


def executar_ui(seed):
    App(seed).rodar()


def captura(seed, caminho, hora):
    """Modo de teste: simula alguns segundos, mede o custo do desenho e salva um quadro."""
    app = App(seed, hora)
    app.luz = [float(v) for v in PRESETS[hora]]
    app.m.ir_para(520, 560)
    dt = 1 / 60
    for _ in range(60 * 14):
        app.m.passo(dt)
        app.atualizar(dt)
    app.mouse = (240, 120)
    t0 = time.perf_counter()
    n = 120
    for _ in range(n):
        app.m.passo(dt)
        app.atualizar(dt)
        app.desenhar(60)
    ms = (time.perf_counter() - t0) / n * 1000
    pygame.image.save(app.tela, caminho)
    print(f"Quadro salvo em {caminho} | passo+desenho: {ms:.1f} ms/quadro ({1000 / ms:.0f} FPS potenciais)")
    print(f"Estado: {app.m.estado} | pedestres: {[p.estado for p in app.m.pedestres]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="DOG-IA V2")
    ap.add_argument("--benchmark", type=int, default=0, help="número de viagens em modo headless")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--trace", action="store_true", help="imprime transições de estado de uma viagem ao Mercado")
    ap.add_argument("--captura", type=str, default=None, help="salva um quadro (PNG) em modo headless")
    ap.add_argument("--hora", choices=list(PRESETS), default="dia")
    a = ap.parse_args()
    if a.benchmark:
        benchmark(a.benchmark, a.seed)
    elif a.trace:
        trace(a.seed)
    elif a.captura:
        captura(a.seed, a.captura, a.hora)
    else:
        executar_ui(a.seed)

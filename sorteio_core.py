import datetime
import hashlib
import json
import math
import os
import random
import re
import sqlite3

try:
    import bcrypt
except ModuleNotFoundError:
    bcrypt = None


EPSILON = 1e-14
FPMIN = 1e-300
ITMAX = 200


def gerar_hash_password(password):
    if bcrypt is not None:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120000)
    return b"pbkdf2$" + salt.hex().encode() + b"$" + digest.hex().encode()


def verificar_password(password, stored_password):
    if bcrypt is not None and not stored_password.startswith(b"pbkdf2$"):
        return bcrypt.checkpw(password.encode(), stored_password)

    algoritmo, salt_hex, digest_hex = stored_password.decode().split("$", 2)
    if algoritmo != "pbkdf2":
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt_hex),
        120000,
    )
    return digest.hex() == digest_hex


def ligar_base_dados(caminho="sistema.db"):
    return sqlite3.connect(caminho)


def obter_colunas_tabela(conn, tabela):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabela})")
    return {linha[1] for linha in cursor.fetchall()}


def garantir_coluna(conn, tabela, coluna, definicao):
    colunas = obter_colunas_tabela(conn, tabela)
    if coluna in colunas:
        return

    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
    conn.commit()


def preparar_base_dados(conn):
    cursor = conn.cursor()

    # Cria a estrutura principal da base de dados para autenticacao,
    # historico de sorteios e auditoria de eventos.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            data TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sorteios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            total INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            participantes TEXT NOT NULL,
            resultado TEXT NOT NULL,
            created_at TEXT NOT NULL,
            chi_square REAL,
            p_value REAL,
            repeticoes INTEGER,
            observacoes TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # Garante compatibilidade com bases antigas que ainda nao tinham
    # todas as colunas introduzidas nas versoes mais recentes.
    garantir_coluna(conn, "users", "created_at", "TEXT")
    garantir_coluna(conn, "sorteios", "chi_square", "REAL")
    garantir_coluna(conn, "sorteios", "p_value", "REAL")
    garantir_coluna(conn, "sorteios", "repeticoes", "INTEGER")
    garantir_coluna(conn, "sorteios", "observacoes", "TEXT")

    cursor.execute("UPDATE users SET created_at = COALESCE(created_at, ?)", (agora_iso(),))
    cursor.execute("UPDATE sorteios SET created_at = COALESCE(created_at, ?)", (agora_iso(),))
    conn.commit()


def agora_iso():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalizar_espacos(texto):
    return re.sub(r"\s+", " ", texto or "").strip()


def limpar_nome(nome):
    return normalizar_espacos(nome)


def limpar_username(username):
    username_limpo = normalizar_espacos(username)
    return re.sub(r"[^A-Za-z0-9_.-]", "", username_limpo)


def limpar_lista_nomes(nomes):
    nomes_limpos = []
    vistos = set()

    for nome in nomes:
        nome_limpo = limpar_nome(nome)
        if not nome_limpo:
            continue

        chave = nome_limpo.casefold()
        if chave in vistos:
            continue

        vistos.add(chave)
        nomes_limpos.append(nome_limpo)

    return nomes_limpos


def criar_utilizador(conn, username, password):
    username_limpo = limpar_username(username)
    if not username_limpo:
        raise ValueError("Informe um utilizador valido.")

    if len(password or "") < 4:
        raise ValueError("A senha deve ter pelo menos 4 caracteres.")

    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = ?", (username_limpo,))
    if cursor.fetchone():
        raise ValueError("Este utilizador ja existe.")

    # A senha nunca e guardada em texto simples; fica sempre armazenada como hash.
    hashed = gerar_hash_password(password)
    cursor.execute(
        "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
        (username_limpo, hashed, agora_iso()),
    )
    conn.commit()
    registar_evento(conn, username_limpo, "CRIACAO_CONTA", "Nova conta criada.")
    return username_limpo


def criar_admin(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE username = ?", ("admin",))
    if cursor.fetchone():
        return

    hashed = gerar_hash_password("1234")
    cursor.execute(
        "INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
        ("admin", hashed, agora_iso()),
    )
    conn.commit()
    registar_evento(conn, "admin", "CRIACAO_CONTA", "Conta padrao inicial criada.")


def autenticar_utilizador(conn, username, password):
    username_limpo = limpar_username(username)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE username = ?", (username_limpo,))
    result = cursor.fetchone()

    # Falhas e sucessos de login sao registados para auditoria do sistema.
    if not result:
        registar_evento(conn, username_limpo or "desconhecido", "LOGIN_FALHOU", "Utilizador nao encontrado.")
        return False, "Utilizador nao existe.", None

    stored_password = result[0]
    if not verificar_password(password or "", stored_password):
        registar_evento(conn, username_limpo, "LOGIN_FALHOU", "Senha incorreta.")
        return False, "Senha incorreta.", None

    data = agora_iso()
    cursor.execute("INSERT INTO logins (username, data) VALUES (?, ?)", (username_limpo, data))
    conn.commit()
    registar_evento(conn, username_limpo, "LOGIN_SUCESSO", f"Entrada no sistema em {data}.")
    return True, "Login efetuado com sucesso.", username_limpo


def registar_evento(conn, username, event_type, details):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO event_logs (username, event_type, details, created_at) VALUES (?, ?, ?, ?)",
        (username or "sistema", event_type, details, agora_iso()),
    )
    conn.commit()


def _gammainc_series(a, x):
    ap = a
    total = 1.0 / a
    delta = total

    for _ in range(ITMAX):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * EPSILON:
            break

    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gammainc_cf(a, x):
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b
    h = d

    for i in range(1, ITMAX + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN

        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN

        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPSILON:
            break

    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gammainc_upper_regularized(a, x):
    if a <= 0:
        raise ValueError("O parametro 'a' deve ser positivo.")

    if x <= 0:
        return 1.0

    if x < a + 1.0:
        return 1.0 - _gammainc_series(a, x)

    return _gammainc_cf(a, x)


def calcular_quiquadrado(contagens):
    # Compara a distribuicao observada com a distribuicao esperada
    # para medir se existe desvio relevante nas selecoes.
    valores = [float(valor) for valor in contagens if valor is not None]
    if len(valores) < 2:
        return 0.0, 1.0

    total = sum(valores)
    if total <= 0:
        return 0.0, 1.0

    esperado = total / len(valores)
    estatistica = sum(((valor - esperado) ** 2) / esperado for valor in valores)
    graus_liberdade = len(valores) - 1
    p_value = gammainc_upper_regularized(graus_liberdade / 2.0, estatistica / 2.0)
    return estatistica, max(0.0, min(1.0, p_value))


def avaliar_imparcialidade(total, quantidade, repeticoes=2000, seed=20260416):
    if total < 2 or quantidade <= 0 or quantidade > total:
        return {
            "chi_square": 0.0,
            "p_value": 1.0,
            "repeticoes": 0,
            "contagens": [],
            "mensagem": "Nao foi possivel calcular o teste de imparcialidade para esta configuracao.",
        }

    # Usa varias simulacoes do sorteio para estimar se o algoritmo
    # distribui as selecoes de forma equilibrada.
    gerador = random.Random(seed)
    contagens = [0] * total

    for _ in range(repeticoes):
        selecionados = gerador.sample(range(total), quantidade)
        for indice in selecionados:
            contagens[indice] += 1

    estatistica, p_value = calcular_quiquadrado(contagens)

    if p_value >= 0.05:
        mensagem = (
            "O teste de Qui-quadrado nao encontrou evidencia estatistica de enviesamento "
            f"na simulacao ({repeticoes} repeticoes, p={p_value:.4f})."
        )
    else:
        mensagem = (
            "O teste de Qui-quadrado encontrou indicios de desvio na simulacao "
            f"({repeticoes} repeticoes, p={p_value:.4f})."
        )

    return {
        "chi_square": estatistica,
        "p_value": p_value,
        "repeticoes": repeticoes,
        "contagens": contagens,
        "mensagem": mensagem,
    }


def realizar_sorteio(total, quantidade, nomes_participantes=None, rng=None):
    if total <= 0 or quantidade <= 0:
        raise ValueError("Os valores devem ser maiores que zero.")

    if quantidade > total:
        raise ValueError("A quantidade sorteada nao pode ser maior que o total.")

    # O sample escolhe elementos sem repeticao, o que impede vencedores duplicados.
    gerador = rng or random
    nomes_limpos = limpar_lista_nomes(nomes_participantes or [])
    numeros = gerador.sample(range(1, total + 1), quantidade)
    selecionados = []

    for numero in numeros:
        if numero <= len(nomes_limpos):
            selecionados.append({"numero": numero, "nome": nomes_limpos[numero - 1]})
        else:
            selecionados.append({"numero": numero, "nome": "(sem nome)"})

    return {
        "numeros": numeros,
        "participantes": nomes_limpos,
        "selecionados": selecionados,
    }


def guardar_sorteio(conn, username, total, quantidade, participantes, selecionados, auditoria):
    cursor = conn.cursor()
    timestamp = agora_iso()
    participantes_json = json.dumps(participantes, ensure_ascii=True)
    resultado_json = json.dumps(selecionados, ensure_ascii=True)
    observacoes = json.dumps(
        {
            "mensagem": auditoria["mensagem"],
            "contagens": auditoria["contagens"],
        },
        ensure_ascii=True,
    )

    # O registo persistido liga operador, parametros e auditoria do sorteio
    # para permitir consulta posterior e rastreabilidade.
    cursor.execute(
        """
        INSERT INTO sorteios (
            username, total, quantidade, participantes, resultado, created_at,
            chi_square, p_value, repeticoes, observacoes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            total,
            quantidade,
            participantes_json,
            resultado_json,
            timestamp,
            auditoria["chi_square"],
            auditoria["p_value"],
            auditoria["repeticoes"],
            observacoes,
        ),
    )
    conn.commit()

    detalhes = (
        f"Sorteio iniciado por {username}: total={total}, quantidade={quantidade}, "
        f"resultado={resultado_json}"
    )
    registar_evento(conn, username, "SORTEIO_EXECUTADO", detalhes)
    return cursor.lastrowid


def listar_sorteios(conn, limite=20):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, total, quantidade, resultado, created_at, chi_square, p_value
        FROM sorteios
        ORDER BY id DESC
        LIMIT ?
        """,
        (limite,),
    )
    return cursor.fetchall()


def listar_eventos(conn, limite=30):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT username, event_type, details, created_at
        FROM event_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        (limite,),
    )
    return cursor.fetchall()

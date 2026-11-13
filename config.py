"""
config.py — Configurações centrais do convite.

Tudo que muda de uma festa para outra (data, hora, local, textos, imagens)
fica aqui. Para alterar o convite, edite apenas este arquivo.
Credenciais (Supabase, senha do admin) NÃO ficam aqui: ficam em
Streamlit Secrets ou variáveis de ambiente (veja get_secret).
"""

import hmac
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
CSS_FILE = BASE_DIR / "styles.css"

# ---------------------------------------------------------------------------
# Informações do evento (fáceis de alterar)
# ---------------------------------------------------------------------------
EVENTO = {
    "titulo": "Aniversário dos Gatos",
    "data_texto": "13 de dezembro",      # usado nas frases da tela
    "data_curta": "13/12/2026",
    "horario": "13h",
    "local": "A CONFIRMAR",
}

# ---------------------------------------------------------------------------
# Imagens (arquivos dentro da pasta assets/)
# ---------------------------------------------------------------------------
IMAGENS = {
    "IMG_2059": "IMG_2059.webp",   # fundo quadriculado/marca d'água: nunca mostrar como transparência
    "IMG_2058": "IMG_2058.webp",
    "IMG_2057": "IMG_2057.jpeg",
    "IMG_2056": "IMG_2056.jpeg",
}

# ---------------------------------------------------------------------------
# Textos das telas (português brasileiro)
# ---------------------------------------------------------------------------
TEXTOS = {
    # Tela 1 — convite
    "t1_titulo": "🐾 Você está convidado! 🐾",
    "t1_sub": "Está chegando uma comemoração muito especial!",
    "t1_data": f"Dia {EVENTO['data_texto']}, às {EVENTO['horario']}.",
    "t1_pergunta": "Você deseja comparecer?",
    "t1_sim": "SIM! 🎉",
    "t1_nao": "NÃO 😢",
    # Tela 2 — brincadeira
    "t2_titulo": "HAHAHAHA! 😂",
    "t2_sub": "Achou que era só isso?",
    "t2_pergunta": "Você vai vir mesmo?",
    "t2_sim": "SIM! ❤️",
    "t2_nao": "NÃO 😭",
    # Tela 3 — cadastro
    "t3_titulo": "AEEE! Sabia que você não ia perder! 🥳",
    "t3_sub": "Agora coloque seu nome na lista de convidados!",
    # Tela 4 — lista
    "t4_titulo": "Quem vai nessa festa? 🐱",
}

# Mensagens exibidas, em ordem, cada vez que o convidado clica em NÃO na 2ª tela
MENSAGENS_NAO = [
    "Os gatos ficaram te olhando torto. 😾 Tenta de novo!",
    "Essa resposta foi tão ruim que a vela do bolo apagou. 🕯️",
    "Um gatinho acabou de derrubar um copo de tristeza. 🙀 Pensa melhor!",
    "Último aviso: vai ter bolo. 🎂 Muda essa resposta!",
]

# ---------------------------------------------------------------------------
# Regras de validação
# ---------------------------------------------------------------------------
NOME_TAMANHO_MAX = 60
TABELA_CONVIDADOS = "convidados"


# ---------------------------------------------------------------------------
# Segredos: Streamlit Secrets primeiro, variável de ambiente como alternativa
# ---------------------------------------------------------------------------
def get_secret(chave: str, padrao: str | None = None) -> str | None:
    """Lê um segredo de st.secrets ou, se não existir, de os.environ."""
    try:
        import streamlit as st
        if chave in st.secrets:
            return str(st.secrets[chave])
    except Exception:
        # Sem Streamlit ou sem secrets.toml: segue para variável de ambiente
        pass
    return os.environ.get(chave, padrao)


# ---------------------------------------------------------------------------
# Senha da área administrativa (vem sempre de Secrets / variável de ambiente)
# ---------------------------------------------------------------------------
SENHA_ADMIN_MODELO = "DEFINA_UMA_SENHA_FORTE"  # valor do modelo: nunca vale como senha


def admin_configurado() -> bool:
    """True se existe uma senha de administrador de verdade."""
    senha = get_secret("ADMIN_PASSWORD")
    return bool(senha) and senha != SENHA_ADMIN_MODELO


def verificar_senha_admin(tentativa: str) -> bool:
    """Compara a senha digitada com a configurada, em tempo constante."""
    if not admin_configurado() or not tentativa:
        return False
    senha = get_secret("ADMIN_PASSWORD")
    return hmac.compare_digest(tentativa.encode("utf-8"), senha.encode("utf-8"))

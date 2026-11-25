"""
database.py — Acesso ao Supabase (PostgreSQL) para a lista de convidados.

Segurança:
  * O app usa a chave de serviço (service_role) do Supabase, guardada apenas
    em Streamlit Secrets / variável de ambiente. Ela roda no servidor do
    Streamlit e nunca é enviada ao navegador do convidado.
  * A tabela tem RLS ligado e nenhuma política: ninguém acessa os dados
    diretamente pela API pública do Supabase, só este app.
  * O token individual NUNCA é devolvido nas consultas públicas.
  * A duplicidade de nomes é garantida pelo próprio banco (índice único),
    então dois cadastros simultâneos com o mesmo nome não passam.
"""

import logging
import re
import secrets

import config


# ---------------------------------------------------------------------------
# Erros com mensagens prontas para mostrar ao convidado
# ---------------------------------------------------------------------------
class ErroBanco(Exception):
    """Falha de conexão, configuração ou consulta ao banco."""


class NomeInvalido(ValueError):
    """Nome vazio ou grande demais."""


class NomeDuplicado(Exception):
    """Já existe convidado com esse nome (ignorando maiúsculas/minúsculas)."""


MSG_BANCO_INDISPONIVEL = (
    "Não consegui falar com o banco de dados agora. 😿 "
    "Tente de novo em alguns instantes."
)

# Logger: a causa real dos erros vai para os logs do servidor
# (no Streamlit Cloud: Manage app > logs), nunca para a tela do convidado.
log = logging.getLogger("streamlit.convite")


def _erro_banco(erro: Exception) -> ErroBanco:
    """Registra a causa verdadeira nos logs e devolve o erro amigável."""
    log.error(
        "Falha no banco de dados: %s: %s", type(erro).__name__, erro, exc_info=erro
    )
    return ErroBanco(MSG_BANCO_INDISPONIVEL)


# Cliente criado sob demanda e reaproveitado entre os visitantes
_cliente = None


def _obter_cliente():
    """Cria (uma vez) e devolve o cliente do Supabase."""
    global _cliente
    if _cliente is None:
        url = config.get_secret("SUPABASE_URL")
        chave = config.get_secret("SUPABASE_KEY")
        if not url or not chave or "COLE_AQUI" in url or "COLE_AQUI" in chave:
            raise ErroBanco(
                "O banco de dados ainda não foi configurado "
                "(faltam SUPABASE_URL e SUPABASE_KEY nos Secrets)."
            )
        try:
            from supabase import create_client
            _cliente = create_client(url, chave)
        except Exception as erro:
            raise _erro_banco(erro) from erro
    return _cliente


def _tabela():
    return _obter_cliente().table(config.TABELA_CONVIDADOS)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
def limpar_nome(nome: str) -> str:
    """Remove espaços nas pontas e reduz espaços repetidos a um só."""
    return re.sub(r"\s+", " ", nome or "").strip()


def validar_nome(nome_bruto: str) -> str:
    """Devolve o nome limpo ou levanta NomeInvalido."""
    nome = limpar_nome(nome_bruto)
    if not nome:
        raise NomeInvalido("Digite seu nome para entrar na lista. 🐱")
    if len(nome) > config.NOME_TAMANHO_MAX:
        raise NomeInvalido(
            f"Nome muito grande! Use até {config.NOME_TAMANHO_MAX} letras."
        )
    return nome


def _eh_duplicidade(erro: Exception) -> bool:
    """Reconhece violação de índice único (código 23505 do PostgreSQL)."""
    return getattr(erro, "code", None) == "23505" or "duplicate key" in str(erro).lower()


# ---------------------------------------------------------------------------
# Operações
# ---------------------------------------------------------------------------
def cadastrar_convidado(nome_bruto: str) -> dict:
    """
    Salva um convidado e devolve {"nome": ..., "token": ...}.
    O token é aleatório e seguro (256 bits) e identifica só este cadastro.
    """
    nome = validar_nome(nome_bruto)
    token = secrets.token_urlsafe(32)
    try:
        _tabela().insert({"nome": nome, "token": token}).execute()
    except ErroBanco:
        raise
    except Exception as erro:
        if _eh_duplicidade(erro):
            raise NomeDuplicado(nome) from erro
        raise _erro_banco(erro) from erro
    return {"nome": nome, "token": token}


def listar_convidados() -> list[dict]:
    """Lista pública: só nome e data. Nunca inclui o token."""
    try:
        resposta = (
            _tabela().select("nome, criado_em").order("criado_em").execute()
        )
    except ErroBanco:
        raise
    except Exception as erro:
        raise _erro_banco(erro) from erro
    return resposta.data or []


def listar_registros() -> list[dict]:
    """
    Uso EXCLUSIVO da área administrativa: id, nome e data de cada cadastro.
    O token continua de fora: o administrador não precisa dele para nada.
    """
    try:
        resposta = (
            _tabela().select("id, nome, criado_em").order("criado_em").execute()
        )
    except ErroBanco:
        raise
    except Exception as erro:
        raise _erro_banco(erro) from erro
    return resposta.data or []


def excluir_por_id(id_convidado: int) -> bool:
    """Uso EXCLUSIVO do administrador: remove um cadastro pelo id."""
    # bool é subtipo de int em Python: recusa True/False explicitamente
    if isinstance(id_convidado, bool) or not isinstance(id_convidado, int) or id_convidado <= 0:
        return False
    try:
        resposta = _tabela().delete().eq("id", id_convidado).execute()
    except ErroBanco:
        raise
    except Exception as erro:
        raise _erro_banco(erro) from erro
    return bool(resposta.data)


# Formato esperado do token (secrets.token_urlsafe): letras, números, "-" e "_"
_FORMATO_TOKEN = re.compile(r"[A-Za-z0-9_-]{20,64}")


def _token_valido(token) -> bool:
    """Descarta lixo antes de consultar o banco."""
    return isinstance(token, str) and _FORMATO_TOKEN.fullmatch(token) is not None


def buscar_por_token(token: str) -> dict | None:
    """Devolve {"nome": ...} do dono do token, ou None se não existir."""
    token = token.strip() if isinstance(token, str) else ""
    if not _token_valido(token):
        return None
    try:
        resposta = (
            _tabela().select("nome").eq("token", token).limit(1).execute()
        )
    except ErroBanco:
        raise
    except Exception as erro:
        raise _erro_banco(erro) from erro
    return resposta.data[0] if resposta.data else None


def excluir_por_token(token: str) -> bool:
    """
    Remove SOMENTE o cadastro que tem exatamente este token.
    Devolve True se removeu, False se o token não existe (ou já foi removido).
    """
    token = token.strip() if isinstance(token, str) else ""
    if not _token_valido(token):
        return False
    try:
        resposta = _tabela().delete().eq("token", token).execute()
    except ErroBanco:
        raise
    except Exception as erro:
        raise _erro_banco(erro) from erro
    return bool(resposta.data)

"""
app.py — Convite interativo de aniversário dos gatos.

Etapas já incluídas:
  2) identidade visual + 1ª tela (convite)
  3) navegação entre telas + brincadeira dos botões (1ª e 2ª telas)
  4) cadastro de convidados no Supabase
  5) lista de convidados + exclusão do próprio nome (por token individual)
  6) área administrativa protegida por senha (acesso por  /?admin )
"""

import html
import random
import time
from base64 import b64encode
from datetime import datetime, timedelta, timezone

import streamlit as st

import config
import database
from config import EVENTO, TEXTOS

st.set_page_config(
    page_title=f"{EVENTO['titulo']} 🎉",
    page_icon="🐱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Descrição (alt) de cada foto, para acessibilidade
ALT = {
    "IMG_2059": "Gato laranja sorrindo com chapéu de festa",
    "IMG_2058": "Gato com chapéu rosa de aniversário",
    "IMG_2057": "Gatinho em pé com chapéu de festa e faixa de feliz aniversário",
    "IMG_2056": "Gato sentado diante de um cupcake com vela acesa",
}


# ---------------------------------------------------------------------------
# JavaScript do botão NÃO fugitivo
# ---------------------------------------------------------------------------
# O botão NÃO é um st.button normal (key="btn_nao_fuga"). O script procura
# esse botão na página e o move para um lugar aleatório da tela quando:
#   - o mouse chega perto (computador);
#   - alguém toca nele (celular).
# O clique é bloqueado, então o NÃO nunca é de fato apertado.
# O botão SIM (key="btn_sim_1") nunca se mexe e é evitado ao sortear posições.
JS_FUGA = r"""
(function (doc, win) {
  if (win.__fugaInstalada) return;      // instala os ouvintes uma única vez
  win.__fugaInstalada = true;

  var DISTANCIA = 90;                    // px de "zona de perigo" ao redor do botão
  var MARGEM = 12;

  function alvo() { return doc.querySelector('.st-key-btn_nao_fuga'); }
  function sim()  { return doc.querySelector('.st-key-btn_sim_1'); }

  function dentro(el, x, y, folga) {
    if (!el) return false;
    var r = el.getBoundingClientRect();
    return x >= r.left - folga && x <= r.right + folga &&
           y >= r.top - folga && y <= r.bottom + folga;
  }

  function mover(px, py) {
    var el = alvo();
    if (!el) return;
    var botao = el.querySelector('button') || el;
    var w = botao.offsetWidth, h = botao.offsetHeight;

    // Na primeira fuga, o botão sai do fluxo da página e passa a flutuar
    el.style.position = 'fixed';
    el.style.width = w + 'px';
    el.style.margin = '0';
    el.style.zIndex = '9999';

    var maxX = Math.max(MARGEM, win.innerWidth - w - MARGEM);
    var maxY = Math.max(MARGEM, win.innerHeight - h - MARGEM);
    var rs = sim() ? sim().getBoundingClientRect() : null;
    var x = MARGEM, y = MARGEM;

    for (var i = 0; i < 30; i++) {
      x = MARGEM + Math.random() * (maxX - MARGEM);
      y = MARGEM + Math.random() * (maxY - MARGEM);
      var cx = x + w / 2, cy = y + h / 2;
      var longeDoPonteiro = (px == null) ||
        Math.hypot(cx - px, cy - py) > 160;
      var foraDoSim = !rs || (x > rs.right + 20 || x + w < rs.left - 20 ||
                              y > rs.bottom + 20 || y + h < rs.top - 20);
      if (longeDoPonteiro && foraDoSim) break;
    }
    el.style.left = x + 'px';
    el.style.top = y + 'px';
  }

  // Computador: o cursor chegou perto -> foge
  doc.addEventListener('pointermove', function (e) {
    if (e.pointerType === 'touch') return;
    var el = alvo();
    if (el && dentro(el.querySelector('button') || el, e.clientX, e.clientY, DISTANCIA)) {
      mover(e.clientX, e.clientY);
    }
  }, true);

  // Celular e computador: tentativa de toque/clique -> bloqueia e foge
  ['pointerdown', 'mousedown', 'touchstart', 'click'].forEach(function (tipo) {
    doc.addEventListener(tipo, function (e) {
      var el = alvo();
      if (el && el.contains(e.target)) {
        e.preventDefault();
        e.stopPropagation();
        var t = e.touches && e.touches[0];
        mover(t ? t.clientX : e.clientX, t ? t.clientY : e.clientY);
      }
    }, { capture: true, passive: false });
  });

  // Se a tela mudar de tamanho, garante que o botão continue visível
  win.addEventListener('resize', function () {
    var el = alvo();
    if (el && el.style.position === 'fixed') mover(null, null);
  });
})
"""


def injetar_js_fuga():
    """Executa o JS_FUGA na página do Streamlit."""
    try:
        # st.html com JavaScript roda direto na página (sem iframe)
        st.html(
            f"<script>{JS_FUGA}(document, window);</script>",
            unsafe_allow_javascript=True,
        )
    except TypeError:
        # Versão antiga do Streamlit: usa iframe e acessa a página pai
        import streamlit.components.v1 as components
        components.html(
            f"<script>{JS_FUGA}(window.parent.document, window.parent);</script>",
            height=0,
        )


# ---------------------------------------------------------------------------
# Auxiliares visuais
# ---------------------------------------------------------------------------
def carregar_css():
    """Injeta o styles.css na página."""
    css = config.CSS_FILE.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


@st.cache_data
def img_uri(chave: str) -> str:
    """Lê a imagem de assets/ e devolve como data URI (preserva o arquivo original)."""
    caminho = config.ASSETS_DIR / config.IMAGENS[chave]
    mime = "image/webp" if caminho.suffix == ".webp" else "image/jpeg"
    dados = b64encode(caminho.read_bytes()).decode()
    return f"data:{mime};base64,{dados}"


@st.cache_data
def decoracao_html() -> str:
    """Confetes, balões e patinhas caindo/subindo ao fundo (sempre os mesmos)."""
    rnd = random.Random(13)
    cores = ["#ff4fa3", "#ffd23f", "#3ec1ff", "#ff8a3d"]
    partes = ['<div class="decor">']
    for _ in range(22):
        partes.append(
            f'<span class="confete" style="left:{rnd.randint(0, 98)}%;'
            f'background:{rnd.choice(cores)};'
            f'animation-duration:{rnd.uniform(6, 12):.1f}s;'
            f'animation-delay:-{rnd.uniform(0, 12):.1f}s"></span>'
        )
    for _ in range(6):
        partes.append(
            f'<span class="balao" style="left:{rnd.randint(2, 92)}%;'
            f'background:{rnd.choice(cores)};'
            f'animation-duration:{rnd.uniform(14, 22):.1f}s;'
            f'animation-delay:-{rnd.uniform(0, 18):.1f}s"></span>'
        )
    for _ in range(6):
        partes.append(
            f'<span class="patinha" style="left:{rnd.randint(2, 94)}%;'
            f'top:{rnd.randint(5, 90)}%;font-size:{rnd.randint(22, 40)}px;'
            f'animation-delay:-{rnd.uniform(0, 5):.1f}s">🐾</span>'
        )
    partes.append("</div>")
    return "".join(partes)  # sem quebras de linha: o markdown não vira bloco de código


def polaroid(chave: str, classe_foto: str, classe_moldura: str = "") -> str:
    """Foto com moldura de polaroid."""
    return (
        f'<div class="polaroid {classe_moldura}">'
        f'<img class="{classe_foto}" src="{img_uri(chave)}" alt="{ALT[chave]}">'
        "</div>"
    )


def texto(classe: str, conteudo: str) -> None:
    st.markdown(f'<div class="{classe}">{conteudo}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------
def ir_para(tela: str) -> None:
    """Troca de tela (usado como callback de botão: não perde o estado)."""
    st.session_state.tela = tela


def tentou_nao() -> None:
    """Conta quantas vezes o convidado clicou em NÃO na 2ª tela."""
    st.session_state.cliques_nao = st.session_state.get("cliques_nao", 0) + 1


# ---------------------------------------------------------------------------
# Telas
# ---------------------------------------------------------------------------
def tela_convite() -> None:
    """Tela 1 — o convite, com o botão NÃO fugitivo."""
    texto("titulo", TEXTOS["t1_titulo"])
    st.markdown(
        '<div class="fotos">'
        + polaroid("IMG_2059", "gato-laranja", "a")
        + polaroid("IMG_2058", "rosa", "b")
        + "</div>",
        unsafe_allow_html=True,
    )
    texto("subtitulo", TEXTOS["t1_sub"])
    texto("destaque", TEXTOS["t1_data"])
    texto("cartao", TEXTOS["t1_pergunta"])

    col_sim, col_nao = st.columns(2)
    with col_sim:
        st.button(
            TEXTOS["t1_sim"], key="btn_sim_1", type="primary",
            width="stretch", on_click=ir_para, args=("brincadeira",),
        )
    with col_nao:
        # O clique é bloqueado pelo JS; este aviso só aparece se algo escapar
        if st.button(TEXTOS["t1_nao"], key="btn_nao_fuga", width="stretch"):
            st.toast("Quase! 😹 Esse botão é arisco.")

    injetar_js_fuga()


def tela_brincadeira() -> None:
    """Tela 2 — a pegadinha. Aqui os dois botões funcionam normalmente."""
    texto("titulo", TEXTOS["t2_titulo"])
    st.markdown(
        '<div class="fotos">' + polaroid("IMG_2057", "quadrada", "solo") + "</div>",
        unsafe_allow_html=True,
    )
    texto("subtitulo", TEXTOS["t2_sub"])
    texto("cartao", TEXTOS["t2_pergunta"])

    # Depois de um NÃO, mostra uma mensagem divertida e os botões continuam ali
    cliques = st.session_state.get("cliques_nao", 0)
    if cliques > 0:
        mensagem = config.MENSAGENS_NAO[(cliques - 1) % len(config.MENSAGENS_NAO)]
        texto("aviso", mensagem)

    col_sim, col_nao = st.columns(2)
    with col_sim:
        st.button(
            TEXTOS["t2_sim"], key="btn_sim_2", type="primary",
            width="stretch", on_click=ir_para, args=("cadastro",),
        )
    with col_nao:
        st.button(
            TEXTOS["t2_nao"], key="btn_nao_2",
            width="stretch", on_click=tentou_nao,
        )


def tela_cadastro() -> None:
    """Tela 3 — o convidado coloca o nome na lista (salvo no Supabase)."""
    texto("titulo", TEXTOS["t3_titulo"])
    st.markdown(
        '<div class="fotos">' + polaroid("IMG_2056", "retrato", "solo") + "</div>",
        unsafe_allow_html=True,
    )

    # Já se cadastrou nesta sessão: mostra a confirmação (evita cadastro duplo)
    meu_cadastro = st.session_state.get("meu_cadastro")
    if meu_cadastro:
        mostrar_confirmacao(meu_cadastro)
        return

    texto("subtitulo", TEXTOS["t3_sub"])

    # st.form: só envia ao clicar no botão (ou Enter), sem recarregar a cada letra
    with st.form("form_cadastro", border=False):
        nome = st.text_input(
            "Seu nome",
            max_chars=config.NOME_TAMANHO_MAX,
            placeholder="Como você quer aparecer na lista?",
        )
        enviado = st.form_submit_button(
            "Confirmar presença 🎉", type="primary", width="stretch"
        )

    if not enviado:
        return

    try:
        cadastro = database.cadastrar_convidado(nome)
    except database.NomeInvalido as erro:
        st.warning(str(erro))
    except database.NomeDuplicado:
        st.warning(
            "Já tem alguém com esse nome na lista! 🙀 "
            "Se já era você, use seu código pessoal em "
            "“Gerenciar minha confirmação”, na lista de convidados. "
            "Se for outra pessoa, use um nome diferente (por exemplo, com sobrenome)."
        )
    except database.ErroBanco as erro:
        st.error(str(erro))  # o texto que digitou continua no campo
    else:
        st.session_state.meu_cadastro = cadastro
        st.rerun()


def mostrar_confirmacao(cadastro: dict) -> None:
    """Mensagem de sucesso + código individual + acesso à lista."""
    if not st.session_state.get("ja_festejou"):
        st.balloons()
        st.session_state.ja_festejou = True

    st.success(f"Presença confirmada, {cadastro['nome']}! 🎉")
    st.markdown(
        "**Guarde seu código pessoal.** Só com ele você consegue "
        "remover seu nome da lista depois:"
    )
    st.code(cadastro["token"], language=None)
    # Se o endereço público do app estiver nos Secrets (APP_URL), mostra o link pronto
    base = (config.get_secret("APP_URL") or "").strip().rstrip("/")
    if base.startswith("http"):
        st.markdown("Ou guarde este link individual:")
        st.code(f"{base}/?token={cadastro['token']}", language=None)
    st.button(
        "Ver quem vai nessa festa 🐱", key="btn_ver_lista",
        type="primary", width="stretch", on_click=ir_para, args=("lista",),
    )


def abrir_gerenciar(token: str) -> None:
    """Vai para a tela 'Sua confirmação' com o token informado."""
    st.session_state.token_gerenciar = (token or "").strip()
    st.session_state.confirmando_exclusao = False
    st.session_state.pop("erro_remocao", None)
    st.session_state.tela = "gerenciar"


def pedir_confirmacao() -> None:
    st.session_state.confirmando_exclusao = True


def cancelar_remocao() -> None:
    st.session_state.confirmando_exclusao = False


def remover_meu_nome() -> None:
    """
    Exclui o cadastro dono do token. A exclusão é feita sempre POR TOKEN,
    nunca por nome, então ninguém consegue apagar o cadastro de outra pessoa.
    """
    token = st.session_state.get("token_gerenciar", "")
    try:
        removeu = database.excluir_por_token(token)
    except database.ErroBanco as erro:
        st.session_state.erro_remocao = str(erro)  # continua na tela de confirmação
        return

    meu = st.session_state.get("meu_cadastro")
    if meu and meu.get("token") == token:
        st.session_state.pop("meu_cadastro", None)  # libera novo cadastro neste aparelho
        st.session_state.pop("ja_festejou", None)
    st.session_state.aviso_lista = (
        "Seu nome foi removido da lista. 😿 Sentiremos sua falta!"
        if removeu else "Esse nome já não estava mais na lista."
    )
    st.session_state.pop("token_gerenciar", None)
    st.session_state.confirmando_exclusao = False
    st.session_state.tela = "lista"


def tela_lista() -> None:
    """Tela 4 — lista pública de confirmados."""
    texto("titulo", TEXTOS["t4_titulo"])

    # Resultado de uma exclusão feita há instantes
    aviso = st.session_state.pop("aviso_lista", None)
    if aviso:
        st.success(aviso)

    # A lista é consultada a cada exibição: sempre reflete cadastros e exclusões
    try:
        convidados = database.listar_convidados()
    except database.ErroBanco as erro:
        st.error(str(erro))
        st.button("Tentar de novo 🔄", key="btn_retentar_lista")
        return

    total = len(convidados)
    texto(
        "contador",
        f"<b>{total}</b> {'confirmação' if total == 1 else 'confirmações'} 🎉",
    )

    meu = st.session_state.get("meu_cadastro")
    meu_nome = database.limpar_nome(meu["nome"]).lower() if meu else None

    if not convidados:
        texto("aviso", "Ninguém confirmou ainda. Seja o primeiro! 🐾")
    else:
        # O nome vem do usuário: html.escape impede que ele injete HTML na página
        chips = []
        for c in convidados:
            sou_eu = meu_nome == database.limpar_nome(c["nome"]).lower()
            classe = "chip eu" if sou_eu else "chip"
            extra = " (você)" if sou_eu else ""
            chips.append(
                f'<span class="{classe}">🐾 {html.escape(c["nome"])}{extra}</span>'
            )
        st.markdown(
            f'<div class="chips">{"".join(chips)}</div>', unsafe_allow_html=True
        )

    # Ao clicar, o Streamlit reexecuta o script e a lista é buscada de novo
    st.button("Atualizar lista 🔄", key="btn_atualizar", width="stretch")

    if not meu:
        st.button(
            "Quero entrar na lista 🐾", key="btn_quero_entrar",
            width="stretch", on_click=ir_para, args=("convite",),
        )

    with st.expander("Gerenciar minha confirmação"):
        if meu:
            st.button(
                "Remover meu nome 😿", key="btn_gerenciar_meu",
                width="stretch", on_click=abrir_gerenciar, args=(meu["token"],),
            )
        st.caption("Tem seu código pessoal? Cole aqui para gerenciar sua confirmação:")
        with st.form("form_codigo", border=False):
            codigo = st.text_input("Código pessoal", max_chars=100)
            usar = st.form_submit_button("Continuar", width="stretch")
        if usar:
            if codigo.strip():
                abrir_gerenciar(codigo)
                st.rerun()
            else:
                st.warning("Cole o código que apareceu quando você confirmou presença.")


def tela_gerenciar() -> None:
    """Tela 'Sua confirmação': o dono do token pode remover o próprio nome."""
    texto("titulo", "Sua confirmação 🐾")
    token = st.session_state.get("token_gerenciar", "")

    def voltar(chave: str) -> None:
        st.button(
            "Voltar para a lista", key=chave,
            width="stretch", on_click=ir_para, args=("lista",),
        )

    try:
        convidado = database.buscar_por_token(token)
    except database.ErroBanco as erro:
        st.error(str(erro))
        st.button("Tentar de novo 🔄", key="btn_retentar_gerenciar")
        voltar("btn_voltar_erro")
        return

    if convidado is None:
        st.warning(
            "Não encontrei nenhuma confirmação com esse código. 🙀 "
            "Ele pode estar errado ou o nome já foi removido."
        )
        voltar("btn_voltar_vazio")
        return

    texto("cartao", f"Você está na lista como <b>{html.escape(convidado['nome'])}</b> 🎉")

    if st.session_state.get("erro_remocao"):
        st.error(st.session_state.erro_remocao)

    if not st.session_state.get("confirmando_exclusao"):
        # 1º passo: pedir a remoção
        st.button(
            "Remover meu nome 😿", key="btn_remover",
            width="stretch", on_click=pedir_confirmacao,
        )
    else:
        # 2º passo: confirmar antes de excluir de verdade
        texto("aviso", "Tem certeza? Seu nome vai sair da lista de convidados.")
        col_sim, col_nao = st.columns(2)
        with col_sim:
            st.button(
                "Sim, remover", key="btn_confirma_remover",
                width="stretch", on_click=remover_meu_nome,
            )
        with col_nao:
            st.button(
                "Não, fico! 🐱", key="btn_cancelar_remover", type="primary",
                width="stretch", on_click=cancelar_remocao,
            )
    voltar("btn_voltar_gerenciar")


# ---------------------------------------------------------------------------
# Área administrativa (acesso: endereço do app + /?admin)
# ---------------------------------------------------------------------------
MAX_TENTATIVAS_SENHA = 5


def formatar_data(valor: str) -> str:
    """Data do banco (UTC) -> dd/mm/aaaa HH:MM no horário de Brasília (UTC-3)."""
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return dt.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return str(valor)


def sair_admin() -> None:
    for chave in ("admin_ok", "admin_confirmar", "erro_admin", "aviso_admin"):
        st.session_state.pop(chave, None)
    st.session_state.tela = "convite"


def pedir_exclusao_admin(id_convidado: int) -> None:
    st.session_state.admin_confirmar = id_convidado


def cancelar_exclusao_admin() -> None:
    st.session_state.pop("admin_confirmar", None)


def excluir_admin(id_convidado: int) -> None:
    """Exclui um convidado (qualquer um) depois da confirmação."""
    st.session_state.pop("admin_confirmar", None)
    st.session_state.pop("erro_admin", None)
    try:
        removeu = database.excluir_por_id(id_convidado)
    except database.ErroBanco as erro:
        st.session_state.erro_admin = str(erro)
        return
    st.session_state.aviso_admin = (
        "Convidado removido." if removeu else "Esse convidado já não estava na lista."
    )


def tela_admin() -> None:
    """Área do administrador: pede a senha e, se correta, mostra o painel."""
    texto("titulo", "Área da festa 🔐")
    if st.session_state.get("admin_ok"):
        painel_admin()
    else:
        login_admin()


def login_admin() -> None:
    if not config.admin_configurado():
        st.error(
            "A senha de administrador ainda não foi configurada. "
            "Defina ADMIN_PASSWORD nos Secrets (ou como variável de ambiente)."
        )
    elif st.session_state.get("admin_falhas", 0) >= MAX_TENTATIVAS_SENHA:
        st.error("Muitas tentativas erradas. Feche esta aba e tente mais tarde.")
    else:
        with st.form("form_admin", border=False):
            senha = st.text_input("Senha do administrador", type="password")
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
        if entrar:
            if config.verificar_senha_admin(senha):
                st.session_state.admin_ok = True
                st.session_state.admin_falhas = 0
                st.rerun()
            else:
                time.sleep(1)  # atrasa quem tenta adivinhar a senha
                st.session_state.admin_falhas = st.session_state.get("admin_falhas", 0) + 1
                st.error("Senha incorreta.")
    st.button(
        "Voltar ao convite", key="btn_admin_voltar",
        width="stretch", on_click=ir_para, args=("convite",),
    )


def painel_admin() -> None:
    try:
        registros = database.listar_registros()
    except database.ErroBanco as erro:
        st.error(str(erro))
        st.button("Tentar de novo 🔄", key="btn_admin_retentar")
        st.button("Sair", key="btn_admin_sair_erro", on_click=sair_admin)
        return

    aviso = st.session_state.pop("aviso_admin", None)
    if aviso:
        st.success(aviso)
    if st.session_state.get("erro_admin"):
        st.error(st.session_state.erro_admin)

    total = len(registros)
    texto("contador", f"<b>{total}</b> {'confirmação' if total == 1 else 'confirmações'} 🎉")

    col_atualizar, col_sair = st.columns(2)
    with col_atualizar:
        st.button("Atualizar lista 🔄", key="btn_admin_atualizar", width="stretch")
    with col_sair:
        st.button("Sair", key="btn_admin_sair", width="stretch", on_click=sair_admin)

    if not registros:
        texto("aviso", "Nenhum convidado cadastrado ainda.")
        return

    confirmando = st.session_state.get("admin_confirmar")
    for r in registros:
        with st.container(border=True):
            col_nome, col_acao = st.columns([3, 2])
            with col_nome:
                st.text(r["nome"])  # texto puro: nada é interpretado como HTML
                st.caption(f"Cadastrado em {formatar_data(r['criado_em'])}")
            with col_acao:
                if confirmando != r["id"]:
                    st.button(
                        "🗑️ Excluir", key=f"btn_admin_del_{r['id']}", width="stretch",
                        on_click=pedir_exclusao_admin, args=(r["id"],),
                    )
            if confirmando == r["id"]:
                st.warning(f"Excluir {r['nome']} da lista?")
                c_sim, c_nao = st.columns(2)
                with c_sim:
                    st.button(
                        "Sim, excluir", key=f"btn_admin_sim_{r['id']}", width="stretch",
                        on_click=excluir_admin, args=(r["id"],),
                    )
                with c_nao:
                    st.button(
                        "Cancelar", key=f"btn_admin_nao_{r['id']}", type="primary",
                        width="stretch", on_click=cancelar_exclusao_admin,
                    )

    with st.expander("Ver registros cadastrados (tabela)"):
        st.dataframe(
            [
                {"id": r["id"], "Nome": r["nome"], "Cadastrado em": formatar_data(r["criado_em"])}
                for r in registros
            ],
            hide_index=True,
            width="stretch",
        )


TELAS = {
    "convite": tela_convite,
    "brincadeira": tela_brincadeira,
    "cadastro": tela_cadastro,
    "lista": tela_lista,
    "gerenciar": tela_gerenciar,
    "admin": tela_admin,
}


def main() -> None:
    carregar_css()
    st.markdown(decoracao_html(), unsafe_allow_html=True)
    st.session_state.setdefault("tela", "convite")

    # Link individual (?token=...): abre direto a tela de gerenciar a confirmação.
    # O token é tirado da barra de endereço para não ficar exposto em prints.
    token_url = st.query_params.get("token")
    if token_url:
        abrir_gerenciar(token_url)
        del st.query_params["token"]

    # Endereço do app + /?admin abre a área administrativa (pede senha)
    if "admin" in st.query_params:
        st.session_state.tela = "admin"
        del st.query_params["admin"]

    TELAS[st.session_state.tela]()


main()

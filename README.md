# 🐱 Convite interativo de aniversário

Convite em Streamlit com banco de dados no Supabase (PostgreSQL).
Idioma: português brasileiro.

## O que o app faz

1. **Convite**: o botão NÃO foge do cursor (computador) e do toque (celular).
2. **Brincadeira**: "HAHAHAHA!", com os dois botões funcionando.
3. **Cadastro**: o convidado coloca o nome; o app gera um código pessoal.
4. **Lista**: "Quem vai nessa festa?", com o total de confirmações.
5. **Remover o próprio nome**: só com o código pessoal e depois de confirmar.
6. **Administração** (`/?admin`): protegida por senha; pode excluir qualquer convidado.

## Arquivos

```
aniversario/
├── app.py            telas e navegação
├── database.py       acesso ao Supabase (cadastro, lista, exclusão)
├── config.py         dados da festa, textos e leitura de segredos
├── styles.css        visual (cores, polaroids, botões, lista)
├── requirements.txt  dependências
├── .gitignore        impede publicar o secrets.toml
├── .streamlit/
│   └── secrets.toml  SEUS segredos (nunca vai para o GitHub)
└── assets/           as 4 fotos
```

Para mudar **data, horário, local ou textos**, edite só o `config.py`
(bloco `EVENTO` e `TEXTOS`). Quando o local for definido, troque
`"A CONFIRMAR"` em `EVENTO["local"]`.

## 1. Banco de dados (Supabase)

1. Crie um projeto em supabase.com.
2. Em **SQL Editor**, rode:

```sql
create table public.convidados (
  id bigint generated always as identity primary key,
  nome text not null check (char_length(btrim(nome)) > 0),
  token text not null unique,
  criado_em timestamptz not null default now()
);

create unique index convidados_nome_unico on public.convidados (lower(nome));

alter table public.convidados enable row level security;
```

3. Em **Settings → API Keys**, copie a chave **secret** (`sb_secret_...`).
   A Project URL está no botão **Connect**.

## 2. Segredos

Edite `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_KEY = "sb_secret_..."
ADMIN_PASSWORD = "uma senha forte só sua"
# APP_URL = "https://seu-app.streamlit.app"   # depois de publicar
```

A chave secret e a senha **nunca** vão no código nem no GitHub.

## 3. Rodar no seu computador

```
pip install -r requirements.txt
python -m streamlit run app.py
```

Abra http://localhost:8501. A área administrativa fica em
http://localhost:8501/?admin

## 4. Publicar

### GitHub

```
git init
git add .
git status
```

Confira que `.streamlit/secrets.toml` **não** aparece na lista. Depois:

```
git commit -m "Convite de aniversário"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/aniversario.git
git push -u origin main
```

(Crie antes o repositório vazio `aniversario` em github.com.)

### Streamlit Community Cloud

1. Entre em share.streamlit.io com sua conta do GitHub.
2. Clique em **Create app** → **Yup, I have an app**.
3. Informe o repositório, a branch `main` e o arquivo `app.py`.
4. Abra **Advanced settings**, cole o conteúdo do seu `secrets.toml`
   no campo **Secrets** e salve.
5. Clique em **Deploy**.
6. Depois que o endereço existir, volte em **App settings → Secrets**,
   acrescente `APP_URL = "https://seu-app.streamlit.app"` e salve.
   Com isso, cada convidado recebe um link individual pronto.

## 5. Checklist antes de divulgar

- [ ] Cadastrei um nome e ele apareceu na lista e no Table Editor do Supabase.
- [ ] O mesmo nome com outras letras maiúsculas foi recusado.
- [ ] Removi meu nome usando o código e confirmei na lista.
- [ ] Tentei um código inventado e nada foi apagado.
- [ ] `/?admin` pede senha, recusa senha errada e exclui um convidado.
- [ ] Testei no celular: o NÃO foge ao toque e o SIM continua acessível.
- [ ] Apaguei os nomes de teste (pelo `/?admin`) antes de enviar o convite.
- [ ] O local deixou de ser "A CONFIRMAR" no `config.py` (quando for definido).

## Segurança, em resumo

- A chave do Supabase fica só no servidor do Streamlit (Secrets).
- A tabela tem RLS ligado e nenhuma política: ninguém acessa os dados
  direto pela API pública do Supabase, só este app.
- Cada cadastro tem um token aleatório de 256 bits; a exclusão é sempre
  por token, nunca por nome.
- Nomes duplicados são barrados pelo próprio banco.
- Nomes digitados são tratados como texto, nunca como HTML.

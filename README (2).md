# Bot de Telegram: lembretes por e-mail + cronograma no calendário

Bot em Python que faz duas coisas:

1. **Lembretes por e-mail:** `/lembrete <texto>` envia o texto para o seu e-mail.
2. **Cronograma → calendário:** você envia o PDF do plano de ensino da disciplina e o bot encontra **provas, trabalhos e entregas**, gera um arquivo `.ics` (abre no Google Agenda, Apple Calendar e Outlook) com lembrete 1 dia antes e envia o arquivo no Telegram e por e-mail.

## Três jeitos de usar

| Modo | Precisa de token/e-mail? | Como rodar |
|---|---|---|
| **Linha de comando** | Não | `python cronograma_cli.py plano.pdf` |
| **Página web (Streamlit)** | Não | `pip install -r requirements-web.txt` e `streamlit run app_web.py` |
| **Bot de Telegram** | Sim | `python bot.py` (veja o passo a passo abaixo) |

Opções da linha de comando: `-o nome.ics` (nome do arquivo), `--lembrete 2` (avisar 2 dias antes), `--todas` (incluir datas que já passaram).

Os três modos usam o mesmo leitor (`cronograma.py`).

## Como o leitor de cronograma funciona
- `cronograma.py` extrai as tabelas do PDF com `pdfplumber`.
- Procura linhas com data (`dd/mm`) cujo conteúdo tenha palavras como *prova*, *trabalho*, *entrega* ou *exame*.
- Descobre o ano pelo campo `SEMESTRE` e o nome da disciplina pelo campo `DISCIPLINA`.
- Ignora datas que já passaram.
- `gerar_ics()` monta o arquivo de calendário (eventos de dia inteiro).

Testado com o plano de ensino de Fundamentos de Sistemas Digitais (PUCRS, 2026/2).
Para rodar o teste: `python teste_cronograma.py`

> Limitação: o leitor foi feito para o formato de tabela dos planos da PUCRS. PDFs com outro layout podem exigir ajustes nas palavras-chave ou na leitura da tabela.

## O que você precisa
- Python 3.10 ou mais novo
- Uma conta do Telegram
- Uma conta Gmail com verificação em duas etapas e uma **senha de app**

## Passo a passo

### 1. Criar o bot no Telegram
1. No Telegram, procure por **@BotFather** e envie `/newbot`.
2. Escolha um nome e um usuário (terminado em `bot`).
3. Copie o **token** que ele te der.

### 2. Criar a senha de app do Gmail
1. Ative a verificação em duas etapas na sua conta Google.
2. Procure por "Senhas de app" nas configurações da conta e gere uma.
3. Copie a senha de 16 letras (não é a sua senha normal).

### 3. Preparar o projeto
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configurar os dados
Copie `.env.example` para `.env` e preencha. Recomendado: preencher `CHAT_ID_PERMITIDO` com o seu chat ID para que só você use o bot.

### 5. Rodar
```bash
python bot.py
```
- Envie `/lembrete entregar o T1 na sexta`, ou
- Envie o PDF do cronograma da disciplina e toque no arquivo `.ics` que o bot devolver.

## Próximos passos (ideias)
- [ ] Colocar a página web online (Streamlit Community Cloud)
- [ ] Pedir o horário das provas e criar eventos com hora
- [ ] Guardar as datas em um banco SQLite e avisar automaticamente
- [ ] Suportar vários PDFs de uma vez
- [ ] Usar a API do Claude para ler PDFs com qualquer layout
- [ ] Colocar o bot online (Render, Railway ou um Raspberry Pi)

## Segurança
O arquivo `.env` está no `.gitignore`. Nunca publique seu token nem sua senha.

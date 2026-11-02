import sqlite3
from datetime import date

def conectar():
    """Conecta ao banco e cria a tabela se não existir."""
    conexao = sqlite3.connect("lembretes.db")
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            data_evento DATE NOT NULL,
            titulo TEXT NOT NULL,
            avisado BOOLEAN DEFAULT 0
        )
    """)
    conexao.commit()
    return conexao

def salvar_evento(chat_id: str, data_evento: date, titulo: str):
    """Salva um novo evento no banco de dados."""
    conexao = conectar()
    cursor = conexao.cursor()
    # Verifica se já existe para não duplicar
    cursor.execute(
        "SELECT id FROM eventos WHERE chat_id = ? AND data_evento = ? AND titulo = ?",
        (chat_id, data_evento.strftime("%Y-%m-%d"), titulo)
    )
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO eventos (chat_id, data_evento, titulo) VALUES (?, ?, ?)",
            (chat_id, data_evento.strftime("%Y-%m-%d"), titulo)
        )
        conexao.commit()
    conexao.close()

def buscar_eventos_de_amanha() -> list:
    """Retorna os eventos que acontecem amanhã e ainda não foram avisados."""
    conexao = conectar()
    cursor = conexao.cursor()
    import datetime
    amanha = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    cursor.execute(
        "SELECT id, chat_id, titulo FROM eventos WHERE data_evento = ? AND avisado = 0",
        (amanha,)
    )
    resultados = cursor.fetchall()
    conexao.close()
    return resultados

def marcar_como_avisado(evento_id: int):
    """Marca um evento como já avisado para não mandar mensagem de novo."""
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("UPDATE eventos SET avisado = 1 WHERE id = ?", (evento_id,))
    conexao.commit()
    conexao.close()

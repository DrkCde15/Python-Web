from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


DB_PATH = Path(__file__).with_name("vendas.db")


class Venda(BaseModel):
    produto: str
    preco: float
    quantidade: int


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY,
                produto TEXT NOT NULL,
                preco REAL NOT NULL,
                quantidade INTEGER NOT NULL
            )
            """
        )

        total = conn.execute("SELECT * FROM vendas").fetchall()
        if total == 0:
            conn.executemany(
                """
                INSERT INTO vendas (id, produto, preco, quantidade)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (1, "Camiseta", 29.99, 55),
                    (2, "Calca Jeans", 59.99, 40),
                    (3, "Tenis", 89.99, 35),
                    (4, "Jaqueta", 99.99, 10),
                ],
            )

        conn.commit()


app = FastAPI()
init_db()

@app.get("/")
def root():
    return {"message": "Bem-vindo ao sistema de vendas!"}

@app.get("/vendas/")
def get_vendas():
    with get_db_connection() as conn:
        total = conn.execute("SELECT * FROM vendas").fetchall()
    return {"Vendas": total}

@app.get("/vendas/{id}")
def get_venda(id: int):
    with get_db_connection() as conn:
        venda = conn.execute(
            "SELECT id, produto, preco, quantidade FROM vendas WHERE id = ?",
            (id,),
        ).fetchone()

    if venda is None:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")
    return dict(venda)

@app.post("/vendas/adicionar/{id}")
def create_venda(id: int, venda: Venda):
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO vendas (id, produto, preco, quantidade)
            VALUES (?, ?, ?, ?)
            """,
            (id, venda.produto, venda.preco, venda.quantidade),
        )
        conn.commit()
    return {"id": id, **venda.model_dump()}

@app.delete("/vendas/deletar/{id}")
def delete_venda(id: int):
    with get_db_connection() as conn:
        cursor = conn.execute("DELETE FROM vendas WHERE id = ?", (id,))
        conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    return {"message": "Venda deletada com sucesso"}

@app.put("/vendas/atualizar/{id}")
def update_venda(id: int, venda: Venda):
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE vendas
            SET produto = ?, preco = ?, quantidade = ?
            WHERE id = ?
            """,
            (venda.produto, venda.preco, venda.quantidade, id),
        )
        conn.commit()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Venda nao encontrada")

    return {"id": id, **venda.model_dump()}

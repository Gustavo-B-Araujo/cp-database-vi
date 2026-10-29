import os
import random
from datetime import datetime, timedelta

from pymongo import MongoClient

random.seed(42)

db = MongoClient(os.environ["MONGO_URL"])["ticketflash"]

for colecao in (db.eventos, db.usuarios, db.pedidos):
    colecao.delete_many({})

CIDADES = [
    ("São Paulo", "Av. Paulista, 1000"),
    ("Rio de Janeiro", "Av. Atlântica, 500"),
    ("Belo Horizonte", "Av. Afonso Pena, 200"),
    ("Curitiba", "Rua XV de Novembro, 300"),
    ("Porto Alegre", "Av. Borges de Medeiros, 150"),
]
CATEGORIAS = ["show", "teatro", "festival", "esporte", "standup"]
NOMES_EVENTOS = [
    "Rock in Sampa", "Noite do Samba", "Festival Verão", "Final do Estadual",
    "Stand-up Night", "Orquestra Sinfônica", "Musical Clássicos", "Pop Fest",
    "Jazz na Praça", "Copa Tech Games",
]

hoje = datetime.now()

eventos = []
for i, nome in enumerate(NOMES_EVENTOS):
    cidade, endereco = CIDADES[i % len(CIDADES)]
    eventos.append({
        "nome": nome,
        "categoria": CATEGORIAS[i % len(CATEGORIAS)],
        "data": hoje + timedelta(days=15 * (i + 1)),
        "local": {"cidade": cidade, "endereco": endereco},
        "atracoes": [f"Atração {i + 1}A", f"Atração {i + 1}B"],
        "setores": [
            {"nome": "pista", "preco": 120.0, "capacidade": 200, "vendidos": 0},
            {"nome": "camarote", "preco": 350.0, "capacidade": 50, "vendidos": 0},
            {"nome": "arquibancada", "preco": 80.0, "capacidade": 300, "vendidos": 0},
        ],
    })
ids_eventos = db.eventos.insert_many(eventos).inserted_ids

usuarios = []
for i in range(20):
    usuarios.append({
        "nome": f"Usuario {i + 1}",
        "email": f"usuario{i + 1}@email.com",
        "cidade": CIDADES[i % len(CIDADES)][0],
        "dataCadastro": hoje - timedelta(days=random.randint(1, 365)),
    })
ids_usuarios = db.usuarios.insert_many(usuarios).inserted_ids

pedidos = []
for _ in range(50):
    i = random.randrange(len(eventos))
    setor = random.choice(eventos[i]["setores"])
    quantidade = random.randint(1, 4)
    status = random.choices(["confirmado", "pendente", "cancelado"], weights=[70, 15, 15])[0]
    if status == "confirmado":
        setor["vendidos"] += quantidade
    pedidos.append({
        "usuarioId": random.choice(ids_usuarios),
        "eventoId": ids_eventos[i],
        "setor": setor["nome"],
        "quantidade": quantidade,
        "valorTotal": setor["preco"] * quantidade,
        "status": status,
        "criadoEm": hoje - timedelta(days=random.randint(0, 30)),
    })
db.pedidos.insert_many(pedidos)

for evento, _id in zip(eventos, ids_eventos):
    db.eventos.update_one({"_id": _id}, {"$set": {"setores": evento["setores"]}})

print(f"{len(eventos)} eventos, {len(usuarios)} usuários, {len(pedidos)} pedidos")

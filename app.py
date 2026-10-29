import os
from datetime import datetime

import redis
from flask import Flask, jsonify, request
from pymongo import MongoClient

from bson import ObjectId
from bson.errors import InvalidId


app = Flask(__name__)

mongo = MongoClient(os.environ["MONGO_URL"])
db = mongo["ticketflash"]
cache = redis.Redis.from_url(os.environ["REDIS_URL"], decode_responses=True)


@app.get("/health")
def health():
    mongo.admin.command("ping")
    cache.ping()
    return jsonify(mongo="ok", redis="ok")


CAMPOS_OBRIGATORIOS = [
    "nome", "categoria", "data", "local", "atracoes", "setores"
    ]


def serializar(evento):
    evento["id"] = str(evento.pop("_id"))
    evento["data"] = evento["data"].isoformat()
    return evento


def converter_id(id):
    try:
        return ObjectId(id)
    except InvalidId:
        return None


@app.post("/eventos")
def criar_evento():
    dados = request.get_json()
    faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in dados]
    if faltando:
        return jsonify(erro=f"campos obrigatórios: {faltando}"), 400
    dados["data"] = datetime.fromisoformat(dados["data"])
    for setor in dados["setores"]:
        setor["vendidos"] = 0
    resultado = db.eventos.insert_one(dados)
    return jsonify(id=str(resultado.inserted_id)), 201


@app.get("/eventos")
def listar_eventos():
    filtro = {}
    categoria = request.args.get("categoria")
    cidade = request.args.get("cidade")
    if categoria:
        filtro["categoria"] = categoria
    if cidade:
        filtro["local.cidade"] = cidade
    return jsonify([serializar(e) for e in db.eventos.find(filtro)])


@app.get("/eventos/<id>")
def buscar_evento(id):
    _id = converter_id(id)
    evento = db.eventos.find_one({"_id": _id}) if _id else None
    if not evento:
        return jsonify(erro="evento não encontrado"), 404
    return jsonify(serializar(evento))


@app.put("/eventos/<id>")
def atualizar_evento(id):
    _id = converter_id(id)
    dados = request.get_json()
    if "data" in dados:
        dados["data"] = datetime.fromisoformat(dados["data"])
    resultado = db.eventos.update_one({"_id": _id}, {"$set": dados}) if _id else None
    if not resultado or resultado.matched_count == 0:
        return jsonify(erro="evento não encontrado"), 404
    return jsonify(mensagem="evento atualizado")


@app.delete("/eventos/<id>")
def remover_evento(id):
    _id = converter_id(id)
    resultado = db.eventos.delete_one({"_id": _id}) if _id else None
    if not resultado or resultado.deleted_count == 0:
        return jsonify(erro="evento não encontrado"), 404
    return jsonify(mensagem="evento removido")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

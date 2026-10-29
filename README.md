# cp-database-vi

- Projeto desenvolvido para a disciplina de Mastering Relational and Non-Relational Database.
- Tem como objetivo desenvolver uma API REST em Python para a TicketFlash, plataforma de venda de ingressos, usando MongoDB como banco principal (eventos, usuários e pedidos) e Redis para cache, reservas temporárias, ranking de eventos mais vistos e limite de requisições.

## Demonstração em vídeo

[Assistir no YouTube](https://youtu.be/VfeEa_tcc3M)

## Autor
- Gustavo Barrios de Araújo
- RM: 563358

## Como executar

Requisitos: Docker com Compose v2.

**1. Subir a aplicação e popular o banco** (obrigatório antes de testar):

```bash
docker compose up --build -d
docker compose run --rm api python seed.py
```

A API fica em `http://localhost:5000`. O `seed.py` popula o banco com 10 eventos,
20 usuários e 50 pedidos, e pode ser executado de novo a qualquer momento.

**2. Testar as requisições:** importe a coleção
[`collection/ticketflash.postman_collection.json`](collection/ticketflash.postman_collection.json)
no Postman ou no Insomnia. Ela traz todas as requisições com os ids do seed já preenchidos
(variáveis `host`, `eventoId` e `usuarioId`), então basta enviá-las.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica a conexão com o MongoDB e o Redis |
| POST | `/eventos` | Cria um evento |
| GET | `/eventos?categoria=&cidade=` | Lista eventos, com filtros opcionais |
| GET | `/eventos/{id}` | Busca um evento (cache de 60 s; o campo `origem` mostra `cache` ou `banco`) |
| PUT | `/eventos/{id}` | Atualiza um evento e invalida o cache |
| DELETE | `/eventos/{id}` | Remove um evento e invalida o cache |
| GET | `/eventos/ranking` | Top 5 eventos mais vistos |
| GET | `/relatorios/faturamento` | Faturamento por evento (pedidos confirmados) |
| GET | `/relatorios/ocupacao/{id}` | Percentual vendido por setor de um evento |
| POST | `/reservas` | Reserva ingressos por 10 minutos (409 se já existe, 429 acima de 10 por minuto) |
| POST | `/pedidos/confirmar` | Confirma o pedido a partir da reserva (410 se expirou) |

## Estruturas no Redis

| Chave | Estrutura | Uso |
|---|---|---|
| `evento:{id}` | String (JSON), TTL de 60 s | cache do evento |
| `reserva:{evento}:{setor}:{usuario}` | String, `SET NX EX 600` | reserva temporária de 10 minutos |
| `ranking:eventos` | Sorted Set (`ZINCRBY`) | ranking dos mais vistos |
| `limite:reserva:{usuario}` | String, `INCR` + `EXPIRE 60` | limite de 10 reservas por minuto |

## Modelagem (MongoDB)

| Coleção | Campos principais | Relação |
|---|---|---|
| `eventos` | nome, categoria, data, local (subdocumento), atracoes (array), setores (array de subdocumentos com nome, preço, capacidade e vendidos) | setores **embutidos** |
| `usuarios` | nome, email (único), cidade, dataCadastro | — |
| `pedidos` | usuarioId, eventoId, setor, quantidade, valorTotal, status, criadoEm | **referencia** usuário e evento |

### Por que embutir os setores no evento
- Os setores só existem dentro de um evento e são sempre lidos junto com ele, então uma única leitura traz tudo.
- Cada evento tem estrutura própria (setores, atrações e local diferentes), o que combina com documentos flexíveis.
- O `vendidos` de um setor é atualizado com `$inc` em um único documento, o que garante a atomicidade da compra sem transação.

### Por que referenciar usuário e evento no pedido
- Os pedidos crescem sem limite. Embuti-los no evento ou no usuário aumentaria o documento indefinidamente e esbarraria no limite de 16 MB.
- Um pedido tem ciclo de vida próprio (pendente, confirmado, cancelado) e é consultado de forma independente, por exemplo nos relatórios de faturamento.
- A ligação é resolvida com `$lookup` quando necessário.

### Por que `local` é um subdocumento e `atracoes` um array
- `local` agrupa cidade e endereço, e a cidade é filtrável com `local.cidade`.
- `atracoes` é uma lista simples de valores, sem estrutura própria.

## Índices

Criados por código na inicialização da API (`app.py`):

| Coleção | Índice | Motivo |
|---|---|---|
| `usuarios` | `email` (único) | impede e-mails duplicados |
| `eventos` | `categoria` + `data` (composto) | acelera a listagem filtrada por categoria e data |
| `pedidos` | `usuarioId` | acelera a busca de pedidos de um usuário |

### Saída do `explain()`

Consulta: eventos da categoria `show` com data futura.

```python
db.eventos.find({"categoria": "show", "data": {"$gte": datetime.now()}}).explain()
```

Para reproduzir: `docker compose run --rm api python explain.py`

Plano vencedor (`winningPlan`):

```json
{
  "stage": "FETCH",
  "inputStage": {
    "stage": "IXSCAN",
    "keyPattern": { "categoria": 1, "data": 1 },
    "indexName": "categoria_1_data_1",
    "isMultiKey": false,
    "isUnique": false,
    "isSparse": false,
    "isPartial": false,
    "indexVersion": 2,
    "direction": "forward",
    "indexBounds": {
      "categoria": ["[\"show\", \"show\"]"],
      "data": ["[new Date(1793287384901), new Date(9223372036854775807)]"]
    }
  }
}
```

O estágio é `IXSCAN` (leitura pelo índice) e não `COLLSCAN` (varredura da coleção inteira):
o MongoDB usou o índice composto `categoria_1_data_1`, com limites exatos em `categoria`
(igualdade) e em `data` (intervalo).

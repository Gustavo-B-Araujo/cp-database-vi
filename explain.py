import json
import os
from datetime import datetime

from pymongo import MongoClient

db = MongoClient(os.environ["MONGO_URL"])["ticketflash"]

filtro = {"categoria": "show", "data": {"$gte": datetime.now()}}
plano = db.eventos.find(filtro).explain()

print(json.dumps(plano["queryPlanner"]["winningPlan"], indent=2))

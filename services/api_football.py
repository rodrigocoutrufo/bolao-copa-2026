import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from models import db, Jogo

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": API_KEY}

TRADUCAO_SELECOES = {
    "Argentina": "Argentina", "Brazil": "Brasil", "France": "França", "Germany": "Alemanha",
    "Italy": "Itália", "Spain": "Espanha", "England": "Inglaterra", "Portugal": "Portugal",
    "Netherlands": "Holanda", "Belgium": "Bélgica", "Croatia": "Croácia", "Uruguay": "Uruguai",
    "Colombia": "Colômbia", "Morocco": "Marrocos", "Japan": "Japão", "South Korea": "Coreia do Sul",
    "United States": "Estados Unidos", "Mexico": "México", "Canada": "Canadá", "Senegal": "Senegal",
    "Switzerland": "Suíça", "Denmark": "Dinamarca", "Sweden": "Suécia", "Norway": "Noruega",
    "Ukraine": "Ucrânia", "Poland": "Polônia", "Turkey": "Turquia", "Egypt": "Egito",
    "Tunisia": "Tunísia", "Cameroon": "Camarões", "Ghana": "Gana", "Ecuador": "Equador",
    "Chile": "Chile", "Peru": "Peru", "Saudi Arabia": "Arábia Saudita", "Australia": "Austrália",
    "New Zealand": "Nova Zelândia", "Iran": "Irã", "Iraq": "Iraque", "Qatar": "Catar"
}

# Tradutor dinâmico de etapas do torneio internacional
# Correção da ordem cronológica das fases da Copa de 48 seleções
MAPA_FASES = {
    "GROUP_STAGE": "Fase de Grupos",
    "ROUND_OF_32": "16 avos de Final",  # Quem passa da fase de grupos cai aqui primeiro
    "ROUND_OF_16": "Oitavas de Final",  # Aqui restam 16 seleções (as oitavas)
    "QUARTER_FINALS": "Quartas de Final",
    "SEMI_FINALS": "Semifinal",
    "THIRD_PLACE": "Terceiro Lugar",
    "FINAL": "Grande Final"
}

def buscar_copa_2026():
    response = requests.get(f"{BASE_URL}/competitions/WC/matches", headers=HEADERS, timeout=15)
    response.raise_for_status()
    return response.json()

def sincronizar_jogos():
    dados = buscar_copa_2026()

    for partida in dados["matches"]:
        if not partida.get("homeTeam") or not partida.get("awayTeam"):
            continue
            
        nome_original_a = partida["homeTeam"].get("name")
        nome_original_b = partida["awayTeam"].get("name")
        
        if not nome_original_a or not nome_original_b:
            continue

        jogo = Jogo.query.get(partida["id"])
        if not jogo:
            jogo = Jogo(id=partida["id"])

        jogo.time_a = TRADUCAO_SELECOES.get(nome_original_a, nome_original_a)
        jogo.time_b = TRADUCAO_SELECOES.get(nome_original_b, nome_original_b)
        jogo.codigo_time_a = partida["homeTeam"].get("crest", "")
        jogo.codigo_time_b = partida["awayTeam"].get("crest", "")
        jogo.status = partida["status"]
        
        # Sincroniza e mapeia o estágio atual da partida
        estagio_api = partida.get("stage", "GROUP_STAGE")
        jogo.stage = MAPA_FASES.get(estagio_api, "Fase de Grupos")

        dt_utc = datetime.strptime(partida["utcDate"], "%Y-%m-%dT%H:%M:%SZ")
        jogo.data_jogo = dt_utc - timedelta(hours=3)

        if partida["score"]["fullTime"]["home"] is not None:
            jogo.gols_a = partida["score"]["fullTime"]["home"]
            jogo.gols_b = partida["score"]["fullTime"]["away"]
            jogo.encerrado = (partida["status"] == "FINISHED")
        else:
            jogo.encerrado = False

        db.session.add(jogo)

    db.session.commit()
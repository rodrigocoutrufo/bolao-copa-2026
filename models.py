from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    campeao = db.Column(db.String(100))          
    campeao_codigo = db.Column(db.String(255))   
    acertos_exatos = db.Column(db.Integer, default=0)
    acertos_vencedor = db.Column(db.Integer, default=0)

class Jogo(db.Model):
    __tablename__ = "jogos"
    id = db.Column(db.Integer, primary_key=True)
    time_a = db.Column(db.String(100), nullable=False)
    time_b = db.Column(db.String(100), nullable=False)
    codigo_time_a = db.Column(db.String(255))
    codigo_time_b = db.Column(db.String(255))
    data_jogo = db.Column(db.DateTime, nullable=False)
    gols_a = db.Column(db.Integer)
    gols_b = db.Column(db.Integer)
    status = db.Column(db.String(50), default="SCHEDULED")
    stage = db.Column(db.String(50), default="Fase de Grupos") # Campo revolucionário para os filtros
    encerrado = db.Column(db.Boolean, default=False)

class Palpite(db.Model):
    __tablename__ = "palpites"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    jogo_id = db.Column(db.Integer, db.ForeignKey("jogos.id"), nullable=False)
    gols_a = db.Column(db.Integer, nullable=False)
    gols_b = db.Column(db.Integer, nullable=False)
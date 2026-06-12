import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Usuario, Jogo, Palpite
from services.pontuacao import calcular_pontos
from services.api_football import sincronizar_jogos

app = Flask(__name__)

# ESTRATÉGIA DE FIXAÇÃO DE BANCO LOCAL:
# Força a criação do banco em um caminho absoluto na raiz do projeto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(BASE_DIR, 'bolao_producao.db')}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --------------------------------------------------------------------------
# CONFIGURAÇÕES AVANÇADAS DE SEGURANÇA DE SESSÃO (Cookies Rígidos)
# --------------------------------------------------------------------------
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY", 
    "4f7b2c9e8a1d3f5b6c7e8d9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c"
)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=1800
)

db.init_app(app)

# Inicializa o banco garantindo que ele não vai resetar o que já existe
with app.app_context():
    db.create_all()

COPA_ENCERRADA = False 
CAMPEAO_REAL = "Brasil"


# --------------------------------------------------------------------------
# CABEÇALHOS DE PROTEÇÃO COMPLEMENTARES (Anti-Injection & CSP)
# --------------------------------------------------------------------------
@app.after_request
def adicionar_cabecalhos_seguranca(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "img-src 'self' data: https://flagcdn.com https://*.football-data.org;"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


# ==========================================================================
# 1. ROTAS DE AUTENTICAÇÃO (LOGIN / CADASTRO)
# ==========================================================================

@app.route("/", methods=["GET", "POST"])
def login():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "")

        if not nome or not senha:
            flash("Por favor, preencha todos os campos.", "danger")
            return render_template("login.html")

        usuario = Usuario.query.filter_by(nome=nome.lower()).first()

        if usuario and check_password_hash(usuario.senha_hash, senha):
            session.clear()
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome
            session["is_admin"] = (usuario.nome.lower() in ["admin", "rodrigim"])
            return redirect(url_for("dashboard"))
        
        flash("Usuário ou senha incorretos.", "danger")

    return render_template("login.html")


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        senha = request.form.get("senha", "")

        if not nome or not senha:
            flash("Preencha todos os campos para se cadastrar.", "danger")
            return render_template("cadastro.html")

        if len(senha) < 6:
            flash("⚽ Erro de Segurança: Sua senha precisa ter no mínimo 6 caracteres!", "danger")
            return render_template("cadastro.html")

        if len(nome) > 30 or len(senha) > 50:
            flash("Dados muito longos. Limite de 30 caracteres para usuário.", "danger")
            return render_template("cadastro.html")

        nome_lower = nome.lower()
        if Usuario.query.filter_by(nome=nome_lower).first():
            flash("Este nome de usuário já está em uso.", "danger")
            return render_template("cadastro.html")

        novo_usuario = Usuario(nome=nome_lower, senha_hash=generate_password_hash(senha))
        db.session.add(novo_usuario)
        db.session.commit()

        flash("Cadastro realizado com sucesso! Faça o seu login.", "success")
        return redirect(url_for("login"))

    return render_template("cadastro.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==========================================================================
# 2. GESTÃO DE PALPITES COM VALIDAÇÃO TEMPORAL RÍGIDA E CONTAGEM
# ==========================================================================

@app.route("/dashboard")
def dashboard():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    uid = session["usuario_id"]
    agora = datetime.now()

    proximo_jogo = Jogo.query.filter(Jogo.data_jogo > agora, Jogo.encerrado == False).order_by(Jogo.data_jogo.asc()).first()
    
    ja_palpitou_proximo = False
    if proximo_jogo:
        palpite_check = Palpite.query.filter_by(usuario_id=uid, jogo_id=proximo_jogo.id).first()
        if palpite_check:
            ja_palpitou_proximo = True

    total_jogos = Jogo.query.count()
    total_palpites = Palpite.query.filter_by(usuario_id=uid).count()
    
    palpites_usuario = Palpite.query.filter_by(usuario_id=uid).all()
    pontos_acumulados = 0
    acertos_exatos = 0
    
    for p in palpites_usuario:
        j = Jogo.query.get(p.jogo_id)
        if j and j.gols_a is not None and j.gols_b is not None:
            pts = calcular_pontos(p.gols_a, p.gols_b, j.gols_a, j.gols_b)
            pontos_acumulados += pts
            if pts == 3:
                acertos_exatos += 1
                
    aproveitamento = round((total_palpites / total_jogos) * 100) if total_jogos > 0 else 0

    return render_template(
        "dashboard.html", 
        total_jogos=total_jogos, 
        total_palpites=total_palpites,
        pontos_acumulados=pontos_acumulados,
        acertos_exatos=acertos_exatos,
        aproveitamento=aproveitamento,
        proximo_jogo=proximo_jogo,
        ja_palpitou_proximo=ja_palpitou_proximo
    )


@app.route("/palpites", methods=["GET"])
def palpites():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    jogos = Jogo.query.order_by(Jogo.data_jogo.asc()).all()
    palpites_usuario = Palpite.query.filter_by(usuario_id=session["usuario_id"]).all()
    palpites_dict = {p.jogo_id: p for p in palpites_usuario}
    usuario_atual = Usuario.query.get(session["usuario_id"])

    if not usuario_atual:
        session.clear()
        return redirect(url_for("login"))

    selecoes_dict = {}
    for j in jogos:
        if j.time_a and j.time_a not in selecoes_dict:
            selecoes_dict[j.time_a] = j.codigo_time_a
        if j.time_b and j.time_b not in selecoes_dict:
            selecoes_dict[j.time_b] = j.codigo_time_b

    selecoes_ordenadas = sorted(
        [{"nome": nome, "bandeira": band} for nome, band in selecoes_dict.items()],
        key=lambda x: x["nome"]
    )

    return render_template(
        "palpites.html", 
        jogos=jogos, 
        palpites=palpites_dict,
        usuario=usuario_atual,
        selecoes=selecoes_ordenadas
    )


@app.route("/salvar_palpite/<int:jogo_id>", methods=["POST"])
def salvar_palpite(jogo_id):
    if "usuario_id" not in session:
        return jsonify({"success": False, "message": "Sessão inválida ou expirada."}), 401

    data = request.get_json() if request.is_json else request.form
    gols_a = data.get("gols_a")
    gols_b = data.get("gols_b")

    if gols_a is None or gols_b is None or str(gols_a).strip() == "" or str(gols_b).strip() == "":
        return jsonify({"success": False, "message": "Placar inválido."}), 400

    jogo = Jogo.query.get(jogo_id)
    if not jogo:
        return jsonify({"success": False, "message": "Jogo não localizado."}), 404

    if datetime.now() >= jogo.data_jogo or jogo.encerrado:
        return jsonify({"success": False, "message": "Bloqueio de segurança: Este confronto já se iniciou ou foi encerrado!"}), 400

    palpite_existente = Palpite.query.filter_by(usuario_id=session["usuario_id"], jogo_id=jogo_id).first()
    if palpite_existente:
        return jsonify({"success": False, "message": "Você já possui um palpite salvo para esta partida."}), 400

    try:
        novo_palpite = Palpite(
            usuario_id=session["usuario_id"],
            jogo_id=jogo_id,
            gols_a=int(gols_a),
            gols_b=int(gols_b)
        )
        db.session.add(novo_palpite)
        db.session.commit()
        return jsonify({"success": True, "message": "Palpite fixado com sucesso!"})
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Erro interno de persistência."}), 500


@app.route("/salvar_campeao", methods=["POST"])
def salvar_campeao():
    if "usuario_id" not in session:
        return jsonify({"success": False, "message": "Sessão expirada."}), 401

    data = request.get_json()
    nome_campeao = data.get("campeao")
    codigo_campeao = data.get("codigo")

    if not nome_campeao or not codigo_campeao:
        return jsonify({"success": False, "message": "Seleção inválida."}), 400

    try:
        usuario = Usuario.query.get(session["usuario_id"])
        if not usuario:
            return jsonify({"success": False, "message": "Usuário inválido."}), 404
        if usuario.campeao:
            return jsonify({"success": False, "message": "Seu campeão definitivo já foi escolhido."}), 400

        usuario.campeao = nome_campeao
        usuario.campeao_codigo = codigo_campeao
        db.session.commit()
        return jsonify({"success": True, "message": f"Campeão definitivo cravado!"})
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Erro ao salvar escolha."}), 500


# ==========================================================================
# 3. RANKING E AUDITORIA SECURE QUERIES
# ==========================================================================

@app.route("/ranking")
def ranking():
    if "usuario_id" not in session:
        return redirect(url_for("login"))

    usuarios = Usuario.query.all()
    ranking_lista = []

    for usuario in usuarios:
        pontos = 0
        palpites_usuario = Palpite.query.filter_by(usuario_id=usuario.id).all()

        for palpite in palpites_usuario:
            jogo = Jogo.query.get(palpite.jogo_id)
            if jogo and jogo.gols_a is not None and jogo.gols_b is not None:
                pontos += calcular_pontos(palpite.gols_a, palpite.gols_b, jogo.gols_a, jogo.gols_b)

        if COPA_ENCERRADA and usuario.campeao and usuario.campeao == CAMPEAO_REAL:
            pontos += 10

        ranking_lista.append({
            "id": usuario.id,
            "nome": usuario.nome, 
            "pontos": pontos,
            "campeao_escolhido": usuario.campeao if usuario.campeao else "Não cravou"
        })

    ranking_lista.sort(key=lambda x: x["pontos"], reverse=True)
    return render_template("ranking.html", ranking=ranking_lista)


@app.route("/api/palpites_usuario/<int:user_id>")
def api_palpites_usuario(user_id):
    if "usuario_id" not in session:
        return jsonify({"error": "Acesso não autorizado"}), 401
        
    palpites_user = Palpite.query.filter_by(usuario_id=user_id).all()
    resultado = []
    
    for p in palpites_user:  # CORRIGIDO DE FORM DEFINTIVA
        jogo = Jogo.query.get(p.jogo_id)
        if jogo and (jogo.encerrado or jogo.status == "FINISHED"):
            pts_obtidos = calcular_pontos(p.gols_a, p.gols_b, jogo.gols_a, jogo.gols_b)
            resultado.append({
                "time_a": jogo.time_a,
                "time_b": jogo.time_b,
                "bandeira_a": jogo.codigo_time_a,
                "bandeira_b": jogo.codigo_time_b,
                "palpite_a": p.gols_a,
                "palpite_b": p.gols_b,
                "resultado_a": jogo.gols_a,
                "resultado_b": jogo.gols_b,
                "pontos": pts_obtidos
            })
    return jsonify({"palpites": resultado})


# ==========================================================================
# 4. PAINEL ADM RESTRICT
# ==========================================================================

@app.route("/admin")
def admin_panel():
    if "usuario_id" not in session or not session.get("is_admin"):
        return "Acesso Negado: Privilégios insuficientes.", 403
    
    total_jogos = Jogo.query.count()
    return render_template("admin.html", total_jogos=total_jogos)


@app.route("/admin/api/sync", methods=["POST"])
def admin_api_sync():
    if "usuario_id" not in session or not session.get("is_admin"):
        return jsonify({"success": False, "message": "Acesso negado."}), 403
    try:
        sincronizar_jogos()
        return jsonify({"success": True, "message": "Sincronização realizada!"})
    except Exception:
        return jsonify({"success": False, "message": "Falha na sincronização."}), 500


@app.route("/admin/api/limpar", methods=["POST"])
def admin_api_limpar():
    if "usuario_id" not in session or not session.get("is_admin"):
        return jsonify({"success": False, "message": "Acesso negado."}), 403
    try:
        Jogo.query.delete()
        db.session.commit()
        return jsonify({"success": True, "message": "Banco limpo."})
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "message": "Erro operacional."}), 500


if __name__ == "__main__":
    app.run(debug=False)
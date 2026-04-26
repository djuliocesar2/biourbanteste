from flask import Flask, render_template, request, redirect, url_for, flash, make_response, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, Usuario, Fazenda, Hortalica, RegistroHidrico
from datetime import datetime
import csv
import io
import numpy as np
from sklearn.linear_model import LinearRegression

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///biourban_pro.db'
app.config['SECRET_KEY'] = 'chave-segura-biourban-2026'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização de extensões
db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Criação das tabelas
with app.app_context():
    db.create_all()

# Filtro para calcular dias no HTML
@app.template_filter('dias_cultivo')
def dias_cultivo_filter(data_plantio_str):
    try:
        data_plantio = datetime.strptime(data_plantio_str, '%Y-%m-%d').date()
        return (datetime.now().date() - data_plantio).days
    except:
        return 0

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login ou senha incorretos.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not Usuario.query.filter_by(username=username).first():
            novo = Usuario(username=username, password=password)
            db.session.add(novo)
            db.session.commit()
            return redirect(url_for('login'))
        flash('Usuário já existe.')
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- DASHBOARD ---

@app.route('/', endpoint='dashboard')
@login_required
def dashboard():
    minhas_fazendas = Fazenda.query.filter_by(usuario_id=current_user.id).all()
    return render_template('dashboard.html', fazendas=minhas_fazendas)

@app.route('/add_fazenda', methods=['POST'])
@login_required
def add_fazenda():
    nome = request.form.get('nome')
    local = request.form.get('localizacao')
    if nome:
        nova = Fazenda(nome=nome, localizacao=local, usuario_id=current_user.id)
        db.session.add(nova)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/fazenda/<int:id>')
@login_required
def ver_fazenda(id):
    fazenda = Fazenda.query.get_or_404(id)
    if fazenda.usuario_id != current_user.id:
        return "Acesso Negado", 403
    
    filtro = request.args.get('filtro', 'Todos')
    hoje = datetime.now().date()
    contagem_variedades = {}
    
    # Lógica de análise de prazos e alertas visuais
    for h in fazenda.hortalicas:
        contagem_variedades[h.nome] = contagem_variedades.get(h.nome, 0) + 1
        if h.status != 'Colhido':
            if h.ciclo_estimado and h.ciclo_estimado > 0:
                d_p = datetime.strptime(h.data_plantio, '%Y-%m-%d').date()
                passados = (hoje - d_p).days
                h.atrasada = passados > h.ciclo_estimado
                h.dias_restantes = max(0, h.ciclo_estimado - passados)
            else:
                h.atrasada, h.dias_restantes = False, 0

    # Coleta de dados para os gráficos
    registros = RegistroHidrico.query.filter(RegistroHidrico.fazenda_id == id).order_by(RegistroHidrico.data_leitura.asc()).all()
    labels_h2o = [r.data_leitura[8:10]+"/"+r.data_leitura[5:7] for r in registros][-15:]
    dados_h2o = [r.consumo_litros for r in registros][-15:]

    stats = {
        'total_ativas': len([h for h in fazenda.hortalicas if h.status != 'Colhido']),
        'tempo_medio': 4.0, # Valor estático ou calculado conforme necessidade
        'filtro_atual': filtro
    }
    
    if filtro == 'Crescendo':
        exibidas = [h for h in fazenda.hortalicas if h.status != 'Colhido']
    elif filtro == 'Colhido':
        exibidas = [h for h in fazenda.hortalicas if h.status == 'Colhido']
    else:
        exibidas = fazenda.hortalicas

    return render_template('index.html', fazenda=fazenda, hortalicas=exibidas, stats=stats, 
                           chart_data=contagem_variedades, labels_h2o=labels_h2o, dados_h2o=dados_h2o)

# --- OPERAÇÕES DE CULTIVO ---

@app.route('/add_hortalica/<int:fazenda_id>', methods=['POST'])
@login_required
def add_hortalica(fazenda_id):
    nome = request.form.get('nome')
    data = request.form.get('data_plantio')
    ciclo = request.form.get('ciclo_estimado')
    if nome and data:
        nova = Hortalica(nome=nome, data_plantio=data, ciclo_estimado=int(ciclo or 0), fazenda_id=fazenda_id)
        db.session.add(nova)
        db.session.commit()
    return redirect(url_for('ver_fazenda', id=fazenda_id))

@app.route('/colher/<int:id>/<int:fazenda_id>', methods=['POST'])
@login_required
def colher(id, fazenda_id):
    h = Hortalica.query.get(id)
    if h:
        h.data_colheita = request.form.get('data_colheita')
        h.status = "Colhido"
        db.session.commit()
    return redirect(url_for('ver_fazenda', id=fazenda_id))

@app.route('/deletar/<int:id>/<int:fazenda_id>')
@login_required
def deletar(id, fazenda_id):
    h = Hortalica.query.get(id)
    if h:
        db.session.delete(h)
        db.session.commit()
    return redirect(url_for('ver_fazenda', id=fazenda_id))

# --- IOT API ---

@app.route('/api/sensor_hidrico', methods=['POST'])
def receber_dados_sensor():
    data = request.get_json()
    if data and 'consumo' in data:
        novo = RegistroHidrico(consumo_litros=data['consumo'], 
                               data_leitura=datetime.now().strftime('%Y-%m-%d'), 
                               fazenda_id=data['fazenda_id'])
        db.session.add(novo)
        db.session.commit()
        return jsonify({"status": "sucesso"}), 201
    return jsonify({"erro": "falha"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=8080)
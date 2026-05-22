from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
import hashlib, os, shutil, json, threading, time, io, zipfile

app = Flask(__name__)
app.config['SECRET_KEY'] = 'inova-carreira-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inova.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─── MODELS ────────────────────────────────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20), default='viewer')  # admin, editor, viewer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Course(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(300), nullable=False)
    tipo          = db.Column(db.String(50))   # pos, profissionalizante, rapido, pacote, terceiros, evento, pratica, projeto
    area          = db.Column(db.String(100))
    horas         = db.Column(db.String(20))
    meses         = db.Column(db.String(20))
    valor         = db.Column(db.String(50))
    link_venda    = db.Column(db.Text)
    descricao     = db.Column(db.Text)
    link_imagem   = db.Column(db.Text)
    insersor      = db.Column(db.String(100))
    obs           = db.Column(db.Text)
    status        = db.Column(db.String(30), default='ativo')  # ativo, descontinuado, em_edicao, oculto
    cupom         = db.Column(db.String(100))
    dono          = db.Column(db.Text)        # para cursos terceiros
    extra_data    = db.Column(db.Text)        # JSON com dados extras (matriz, disciplinas, etc.)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by    = db.Column(db.Integer, db.ForeignKey('user.id'))

class Discipline(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    modulo    = db.Column(db.String(100))
    ordem     = db.Column(db.Integer)
    nome      = db.Column(db.String(300), nullable=False)
    carga     = db.Column(db.String(20))
    professor = db.Column(db.String(200))
    cod_moodle= db.Column(db.String(50))
    titulacao = db.Column(db.String(50))

class AuditLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('user.id'))
    username   = db.Column(db.String(80))
    action     = db.Column(db.String(50))   # criar, editar, excluir, login
    entity     = db.Column(db.String(50))   # course, user, cupom
    entity_id  = db.Column(db.Integer)
    detail     = db.Column(db.Text)         # JSON do que mudou
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    nome         = db.Column(db.String(100), nullable=False)
    quantidade   = db.Column(db.Integer)
    desconto     = db.Column(db.Float)
    cursos_tipo  = db.Column(db.String(100))
    limite_curso = db.Column(db.Integer)
    uso_unico    = db.Column(db.Boolean, default=True)
    data_inicial = db.Column(db.Date)
    data_final   = db.Column(db.Date)
    obs          = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

class Refund(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    colab            = db.Column(db.String(100))
    nome_aluno       = db.Column(db.String(200))
    data_compra      = db.Column(db.Date)
    data_solicitacao = db.Column(db.Date)
    valor            = db.Column(db.Float)
    valor_estorno    = db.Column(db.Float)
    nome_curso       = db.Column(db.String(300))
    categoria        = db.Column(db.String(100))
    motivo           = db.Column(db.Text)
    data_aprovacao   = db.Column(db.Date)
    obs              = db.Column(db.Text)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

class BackupRecord(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    filename   = db.Column(db.String(200))
    size_kb    = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tipo       = db.Column(db.String(20), default='auto')  # auto, manual

# ─── HELPERS ───────────────────────────────────────────────────────────────────

def hash_pw(pw): return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        u = User.query.get(session['user_id'])
        if not u or u.role != 'admin':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def editor_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        u = User.query.get(session['user_id'])
        if not u or u.role not in ('admin', 'editor'):
            flash('Sem permissão para editar.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def log_action(user_id, username, action, entity, entity_id, detail=''):
    entry = AuditLog(user_id=user_id, username=username, action=action,
                     entity=entity, entity_id=entity_id, detail=detail)
    db.session.add(entry)
    db.session.commit()

def make_backup():
    with app.app_context():
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        src = os.path.join(app.instance_path, 'inova.db')
        if not os.path.exists(src): return
        fname = f'backup_{ts}.zip'
        fpath = os.path.join('backups', fname)
        os.makedirs('backups', exist_ok=True)
        with zipfile.ZipFile(fpath, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(src, 'inova.db')
        size_kb = os.path.getsize(fpath) / 1024
        rec = BackupRecord(filename=fname, size_kb=round(size_kb, 2), tipo='auto')
        db.session.add(rec)
        db.session.commit()
        # Keep only last 20 backups
        bks = BackupRecord.query.order_by(BackupRecord.created_at.asc()).all()
        if len(bks) > 20:
            for old in bks[:-20]:
                try: os.remove(os.path.join('backups', old.filename))
                except: pass
                db.session.delete(old)
            db.session.commit()

def backup_scheduler():
    while True:
        time.sleep(7 * 24 * 3600)  # weekly
        make_backup()

@app.context_processor
def inject_now():
    return {'now': datetime.now}

# ─── AUTH ROUTES ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(username=request.form['username']).first()
        if u and u.password == hash_pw(request.form['password']):
            session['user_id'] = u.id
            session['username'] = u.username
            session['role'] = u.role
            log_action(u.id, u.username, 'login', 'user', u.id)
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha incorretos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─── DASHBOARD ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    total     = Course.query.count()
    ativos    = Course.query.filter_by(status='ativo').count()
    em_edicao = Course.query.filter_by(status='em_edicao').count()
    desc      = Course.query.filter_by(status='descontinuado').count()
    por_tipo  = db.session.query(Course.tipo, db.func.count(Course.id))\
                          .group_by(Course.tipo).all()
    recentes  = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    ultimo_bk = BackupRecord.query.order_by(BackupRecord.created_at.desc()).first()
    return render_template('dashboard.html',
        total=total, ativos=ativos, em_edicao=em_edicao, desc=desc,
        por_tipo=por_tipo, recentes=recentes, ultimo_bk=ultimo_bk)

# ─── COURSES ───────────────────────────────────────────────────────────────────

@app.route('/cursos')
@login_required
def cursos():
    tipo   = request.args.get('tipo','')
    area   = request.args.get('area','')
    status = request.args.get('status','')
    busca  = request.args.get('q','')
    q = Course.query
    if tipo:   q = q.filter_by(tipo=tipo)
    if area:   q = q.filter_by(area=area)
    if status: q = q.filter_by(status=status)
    if busca:  q = q.filter(Course.nome.ilike(f'%{busca}%'))
    cursos = q.order_by(Course.nome).all()
    areas  = [r[0] for r in db.session.query(Course.area).distinct().all() if r[0]]
    return render_template('cursos.html', cursos=cursos, areas=areas,
                           filtro_tipo=tipo, filtro_area=area, filtro_status=status, busca=busca)

@app.route('/cursos/novo', methods=['GET','POST'])
@editor_required
def curso_novo():
    if request.method == 'POST':
        d = request.form
        extra = {}
        # matrix fields passed as JSON string
        if d.get('disciplinas_json'):
            extra['disciplinas'] = json.loads(d['disciplinas_json'])
        c = Course(
            nome=d['nome'], tipo=d['tipo'], area=d.get('area',''),
            horas=d.get('horas',''), meses=d.get('meses',''), valor=d.get('valor',''),
            link_venda=d.get('link_venda',''), descricao=d.get('descricao',''),
            link_imagem=d.get('link_imagem',''), insersor=session['username'],
            obs=d.get('obs',''), status=d.get('status','em_edicao'),
            cupom=d.get('cupom',''), dono=d.get('dono',''),
            extra_data=json.dumps(extra, ensure_ascii=False),
            created_by=session['user_id']
        )
        db.session.add(c)
        db.session.flush()
        # Save disciplines separately
        discs = json.loads(d.get('disciplinas_json','[]') or '[]')
        for i, disc in enumerate(discs):
            dd = Discipline(course_id=c.id, modulo=disc.get('modulo',''),
                           ordem=i+1, nome=disc.get('nome',''),
                           carga=disc.get('carga',''), professor=disc.get('professor',''),
                           cod_moodle=disc.get('cod_moodle',''), titulacao=disc.get('titulacao',''))
            db.session.add(dd)
        db.session.commit()
        log_action(session['user_id'], session['username'], 'criar', 'course', c.id, c.nome)
        flash('Curso criado com sucesso!', 'success')
        return redirect(url_for('curso_detalhe', id=c.id))
    tipos = ['pos','profissionalizante','rapido','pacote','terceiros','evento','pratica_conectada','pratica_estagio','projeto_ambiental','ggbr','integra_edu']
    return render_template('curso_form.html', curso=None, tipos=tipos)

@app.route('/cursos/<int:id>')
@login_required
def curso_detalhe(id):
    c    = Course.query.get_or_404(id)
    disc = Discipline.query.filter_by(course_id=id).order_by(Discipline.ordem).all()
    logs = AuditLog.query.filter_by(entity='course', entity_id=id)\
                         .order_by(AuditLog.timestamp.desc()).all()
    extra = json.loads(c.extra_data) if c.extra_data else {}
    return render_template('curso_detalhe.html', c=c, disc=disc, logs=logs, extra=extra)

@app.route('/cursos/<int:id>/editar', methods=['GET','POST'])
@editor_required
def curso_editar(id):
    c = Course.query.get_or_404(id)
    if request.method == 'POST':
        old_nome = c.nome
        d = request.form
        c.nome=d['nome']; c.tipo=d['tipo']; c.area=d.get('area','')
        c.horas=d.get('horas',''); c.meses=d.get('meses',''); c.valor=d.get('valor','')
        c.link_venda=d.get('link_venda',''); c.descricao=d.get('descricao','')
        c.link_imagem=d.get('link_imagem',''); c.obs=d.get('obs','')
        c.status=d.get('status',c.status); c.cupom=d.get('cupom','')
        c.dono=d.get('dono',''); c.updated_at=datetime.utcnow()
        # Update disciplines
        if d.get('disciplinas_json') is not None:
            Discipline.query.filter_by(course_id=id).delete()
            discs = json.loads(d.get('disciplinas_json','[]') or '[]')
            for i, disc in enumerate(discs):
                dd = Discipline(course_id=id, modulo=disc.get('modulo',''),
                               ordem=i+1, nome=disc.get('nome',''),
                               carga=disc.get('carga',''), professor=disc.get('professor',''),
                               cod_moodle=disc.get('cod_moodle',''), titulacao=disc.get('titulacao',''))
                db.session.add(dd)
        db.session.commit()
        log_action(session['user_id'], session['username'], 'editar', 'course', id, f'{old_nome} → {c.nome}')
        flash('Curso atualizado!', 'success')
        return redirect(url_for('curso_detalhe', id=id))
    disc = Discipline.query.filter_by(course_id=id).order_by(Discipline.ordem).all()
    tipos = ['pos','profissionalizante','rapido','pacote','terceiros','evento','pratica_conectada','pratica_estagio','projeto_ambiental','ggbr','integra_edu']
    return render_template('curso_form.html', curso=c, disc=disc, tipos=tipos)

@app.route('/cursos/<int:id>/arquivar', methods=['POST'])
@editor_required
def curso_arquivar(id):
    c = Course.query.get_or_404(id)
    c.status = 'descontinuado'
    db.session.commit()
    log_action(session['user_id'], session['username'], 'arquivar', 'course', id, c.nome)
    flash('Curso arquivado (não excluído).', 'warning')
    return redirect(url_for('cursos'))

# Admins can hard-delete
@app.route('/cursos/<int:id>/excluir', methods=['POST'])
@admin_required
def curso_excluir(id):
    c = Course.query.get_or_404(id)
    nome = c.nome
    Discipline.query.filter_by(course_id=id).delete()
    db.session.delete(c)
    db.session.commit()
    log_action(session['user_id'], session['username'], 'excluir', 'course', id, nome)
    flash(f'Curso "{nome}" excluído permanentemente.', 'danger')
    return redirect(url_for('cursos'))

# ─── API SEARCH ────────────────────────────────────────────────────────────────

@app.route('/api/busca')
@login_required
def api_busca():
    q = request.args.get('q','')
    if len(q) < 2: return jsonify([])
    results = Course.query.filter(Course.nome.ilike(f'%{q}%')).limit(10).all()
    return jsonify([{'id': c.id, 'nome': c.nome, 'tipo': c.tipo, 'status': c.status} for c in results])

# ─── CUPONS ────────────────────────────────────────────────────────────────────

@app.route('/cupons')
@login_required
def cupons():
    cupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('cupons.html', cupons=cupons)

@app.route('/cupons/novo', methods=['GET','POST'])
@editor_required
def cupom_novo():
    if request.method == 'POST':
        d = request.form
        def parse_date(s):
            try: return datetime.strptime(s, '%Y-%m-%d').date()
            except: return None
        cp = Coupon(nome=d['nome'], quantidade=int(d.get('quantidade',0) or 0),
                    desconto=float(d.get('desconto',0) or 0),
                    cursos_tipo=d.get('cursos_tipo',''), limite_curso=int(d.get('limite_curso',1) or 1),
                    uso_unico=(d.get('uso_unico')=='SIM'),
                    data_inicial=parse_date(d.get('data_inicial','')),
                    data_final=parse_date(d.get('data_final','')),
                    obs=d.get('obs',''))
        db.session.add(cp)
        db.session.commit()
        log_action(session['user_id'], session['username'], 'criar', 'cupom', cp.id, cp.nome)
        flash('Cupom criado!', 'success')
        return redirect(url_for('cupons'))
    return render_template('cupom_form.html', cupom=None)

@app.route('/cupons/<int:id>/editar', methods=['GET','POST'])
@editor_required
def cupom_editar(id):
    cp = Coupon.query.get_or_404(id)
    if request.method == 'POST':
        d = request.form
        def parse_date(s):
            try: return datetime.strptime(s, '%Y-%m-%d').date()
            except: return None
        cp.nome=d['nome']; cp.quantidade=int(d.get('quantidade',0) or 0)
        cp.desconto=float(d.get('desconto',0) or 0)
        cp.cursos_tipo=d.get('cursos_tipo','')
        cp.limite_curso=int(d.get('limite_curso',1) or 1)
        cp.uso_unico=(d.get('uso_unico')=='SIM')
        cp.data_inicial=parse_date(d.get('data_inicial',''))
        cp.data_final=parse_date(d.get('data_final',''))
        cp.obs=d.get('obs','')
        db.session.commit()
        log_action(session['user_id'], session['username'], 'editar', 'cupom', id, cp.nome)
        flash('Cupom atualizado!', 'success')
        return redirect(url_for('cupons'))
    return render_template('cupom_form.html', cupom=cp)

# ─── REEMBOLSOS ────────────────────────────────────────────────────────────────

@app.route('/reembolsos')
@login_required
def reembolsos():
    items = Refund.query.order_by(Refund.created_at.desc()).all()
    return render_template('reembolsos.html', items=items)

@app.route('/reembolsos/novo', methods=['GET','POST'])
@editor_required
def reembolso_novo():
    if request.method == 'POST':
        d = request.form
        def pd2(s):
            try: return datetime.strptime(s, '%Y-%m-%d').date()
            except: return None
        r = Refund(colab=d.get('colab',''), nome_aluno=d.get('nome_aluno',''),
                   data_compra=pd2(d.get('data_compra','')),
                   data_solicitacao=pd2(d.get('data_solicitacao','')),
                   valor=float(d.get('valor',0) or 0),
                   valor_estorno=float(d.get('valor_estorno',0) or 0),
                   nome_curso=d.get('nome_curso',''), categoria=d.get('categoria',''),
                   motivo=d.get('motivo',''),
                   data_aprovacao=pd2(d.get('data_aprovacao','')),
                   obs=d.get('obs',''))
        db.session.add(r)
        db.session.commit()
        log_action(session['user_id'], session['username'], 'criar', 'reembolso', r.id, r.nome_aluno)
        flash('Reembolso registrado!', 'success')
        return redirect(url_for('reembolsos'))
    return render_template('reembolso_form.html', item=None)

# ─── HISTÓRICO / AUDIT ─────────────────────────────────────────────────────────

@app.route('/historico')
@login_required
def historico():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50)
    return render_template('historico.html', logs=logs)

# ─── USUÁRIOS ──────────────────────────────────────────────────────────────────

@app.route('/usuarios')
@admin_required
def usuarios():
    users = User.query.all()
    return render_template('usuarios.html', users=users)

@app.route('/usuarios/novo', methods=['GET','POST'])
@admin_required
def usuario_novo():
    if request.method == 'POST':
        d = request.form
        if User.query.filter_by(username=d['username']).first():
            flash('Usuário já existe.', 'danger')
        else:
            u = User(username=d['username'], password=hash_pw(d['password']), role=d['role'])
            db.session.add(u)
            db.session.commit()
            log_action(session['user_id'], session['username'], 'criar', 'user', u.id, u.username)
            flash('Usuário criado!', 'success')
            return redirect(url_for('usuarios'))
    return render_template('usuario_form.html', user=None)

@app.route('/usuarios/<int:id>/editar', methods=['GET','POST'])
@admin_required
def usuario_editar(id):
    u = User.query.get_or_404(id)
    if request.method == 'POST':
        d = request.form
        u.role = d['role']
        if d.get('password'):
            u.password = hash_pw(d['password'])
        db.session.commit()
        log_action(session['user_id'], session['username'], 'editar', 'user', id, u.username)
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('usuarios'))
    return render_template('usuario_form.html', user=u)

@app.route('/usuarios/<int:id>/excluir', methods=['POST'])
@admin_required
def usuario_excluir(id):
    u = User.query.get_or_404(id)
    if u.id == session['user_id']:
        flash('Você não pode excluir sua própria conta.', 'danger')
        return redirect(url_for('usuarios'))
    username = u.username
    db.session.delete(u)
    db.session.commit()
    log_action(session['user_id'], session['username'], 'excluir', 'user', id, username)
    flash(f'Usuário "{username}" excluído.', 'success')
    return redirect(url_for('usuarios'))

# ─── BACKUP ────────────────────────────────────────────────────────────────────

@app.route('/backup/manual', methods=['POST'])
@admin_required
def backup_manual():
    with app.app_context():
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        src = os.path.join(app.instance_path, 'inova.db')
        fname = f'manual_{ts}.zip'
        fpath = os.path.join('backups', fname)
        os.makedirs('backups', exist_ok=True)
        with zipfile.ZipFile(fpath, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(src, 'inova.db')
        size_kb = os.path.getsize(fpath) / 1024
        rec = BackupRecord(filename=fname, size_kb=round(size_kb,2), tipo='manual')
        db.session.add(rec)
        db.session.commit()
    flash('Backup manual criado com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/backup/download/<int:id>')
@admin_required
def backup_download(id):
    rec = BackupRecord.query.get_or_404(id)
    fpath = os.path.join('backups', rec.filename)
    return send_file(fpath, as_attachment=True, download_name=rec.filename)

@app.route('/backup/lista')
@admin_required
def backup_lista():
    bks = BackupRecord.query.order_by(BackupRecord.created_at.desc()).all()
    return render_template('backups.html', bks=bks)

# ─── SEED DATA ─────────────────────────────────────────────────────────────────

def seed_data():
    if User.query.count() > 0: return
    # Create admin
    admin = User(username='admin', password=hash_pw('inova2024'), role='admin')
    junior = User(username='junior', password=hash_pw('inova2024'), role='editor')
    felipe = User(username='felipe', password=hash_pw('inova2024'), role='editor')
    viewer = User(username='visualizador', password=hash_pw('inova2024'), role='viewer')
    db.session.add_all([admin, junior, felipe, viewer])
    db.session.commit()

    # Import data from excel
    try:
        import openpyxl, json as jsonlib
        excel_path = os.path.join(os.path.dirname(__file__), 'CURSOS INOVA - LINKS (1).xlsx')
        wb = openpyxl.load_workbook(excel_path)

        def add_course(nome, tipo, area, horas, valor, link, desc, obs, status, insersor, meses='', cupom='', dono=''):
            if not nome or str(nome).strip() == '': return None
            c = Course(nome=str(nome)[:300], tipo=tipo, area=str(area or '')[:100],
                      horas=str(horas or '')[:20], meses=str(meses or '')[:20],
                      valor=str(valor or '')[:50], link_venda=str(link or '')[:500],
                      descricao=str(desc or ''), obs=str(obs or ''),
                      status=status, insersor=str(insersor or '')[:100],
                      cupom=str(cupom or '')[:100], dono=str(dono or ''),
                      created_by=admin.id)
            db.session.add(c)
            return c

        # PÓS MATRIZES
        ws = wb['PÓS- MATRIZES INOVA']
        for row in ws.iter_rows(min_row=3, values_only=True):
            if not row[1]: continue
            add_course(row[1], 'pos', row[2], row[3], row[5], row[7], '', str(row[8] or ''), 'ativo', row[6], meses=str(row[4] or ''))

        # PROFISSIONALIZANTES
        ws = wb['PROFISSIONALIZANTES INOVA']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1] or str(row[1]).startswith('CURSOS'): continue
            add_course(row[1], 'profissionalizante', row[2], row[3], '', row[4], str(row[5] or ''), str(row[7] or ''), 'ativo', 'INOVA')

        # RÁPIDOS
        ws = wb['RÁPIDOS INOVA']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1]: continue
            add_course(row[1], 'rapido', row[2], row[3], row[5], row[4], str(row[6] or ''), str(row[8] or ''), 'ativo', 'INOVA')

        # PACOTES
        ws = wb['PACOTE CURSOS']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1] or str(row[1]).startswith('Nº'): continue
            add_course(row[1], 'pacote', row[2], row[3], row[8], row[4], '', str(row[6] or ''), 'ativo', str(row[5] or ''))

        # TERCEIROS
        ws = wb['CURSOS TERCEIROS INOVA']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1]: continue
            s = 'descontinuado' if str(row[10] or '').upper().find('DESCONTINUADO') >= 0 else 'ativo'
            add_course(row[1], 'terceiros', row[5], row[3], row[2], row[6], str(row[8] or ''), str(row[10] or ''), s, '', dono=str(row[7] or ''))

        # EVENTOS
        ws = wb['EVENTOS']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[2]: continue
            add_course(row[2], 'evento', 'EVENTO', row[3], row[6], row[4], '', str(row[8] or ''), 'ativo', 'INOVA')

        # PRÁTICAS CONECTADAS
        ws = wb['PRÁTICAS CONECTADAS']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1]: continue
            add_course(row[1], 'pratica_conectada', row[0], '', '', row[3], '', '', 'oculto', 'INOVA', cupom=str(row[2] or ''))

        # PRÁTICAS ESTÁGIO
        ws = wb['PRÁTICAS DE ESTÁGIO']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]: continue
            add_course(row[0], 'pratica_estagio', row[1], '', '', str(row[5] or ''), '', '', 'ativo', str(row[3] or ''), cupom=str(row[4] or ''))

        # PROJ. AMBIENTES PROF
        ws = wb['PROJ. AMBIENTES PROF']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1]: continue
            add_course(row[1], 'projeto_ambiental', '', '', '', str(row[3] or ''), '', str(row[4] or ''), 'oculto', 'INOVA', cupom=str(row[2] or ''))

        # GGBR RÁPIDOS
        ws = wb['GGBR - RÁPIDOS']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1]: continue
            add_course(row[1], 'ggbr', row[2], row[3], row[5], row[4], '', '', 'ativo', 'INOVA')

        # CUPONS
        ws = wb['CUPOM']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0]: continue
            def pd(v):
                if isinstance(v, datetime): return v.date()
                return None
            cp = Coupon(nome=str(row[0])[:100], quantidade=int(row[1] or 0),
                       desconto=float(row[2] or 0), cursos_tipo=str(row[3] or ''),
                       limite_curso=int(row[4] or 1), uso_unico=(str(row[5] or '').upper()=='SIM'),
                       data_inicial=pd(row[6]), obs=str(row[8] or ''))
            db.session.add(cp)

        # REEMBOLSOS
        ws = wb['REEMBOLSOS']
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[1]: continue
            def pd2(v):
                if isinstance(v, datetime): return v.date()
                return None
            r = Refund(colab=str(row[0] or ''), nome_aluno=str(row[1] or ''),
                      data_compra=pd2(row[2]), data_solicitacao=pd2(row[3]),
                      valor=float(row[4] or 0), valor_estorno=float(row[5] or 0),
                      nome_curso=str(row[6] or ''), categoria=str(row[7] or ''),
                      data_aprovacao=pd2(row[10]), motivo=str(row[11] or ''))
            db.session.add(r)

        db.session.commit()
        print("[OK] Dados importados com sucesso!")
    except FileNotFoundError:
        print("[INFO] Arquivo Excel nao encontrado. Iniciando sem dados pre-carregados.")
        db.session.rollback()
    except Exception as e:
        print(f"[ERRO] Ao importar Excel: {e}")
        db.session.rollback()

# ─── INIT ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    t = threading.Thread(target=backup_scheduler, daemon=True)
    t.start()
    app.run(debug=True, host='0.0.0.0', port=5000)

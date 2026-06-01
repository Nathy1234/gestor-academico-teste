from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
import hashlib, os, shutil, json, threading, time, io, zipfile

app = Flask(__name__)

AREAS_VALIDAS = [
    'EDUCAÇÃO', 'SAÚDE', 'NEGÓCIOS', 'TECNOLOGIA',
    'CRIATIVIDADE', 'GASTRONOMIA', 'EVENTO',
]
TIPOS_CURSO = [
    'pos', 'profissionalizante', 'rapido', 'pacote', 'terceiros',
    'evento', 'pratica_conectada', 'pratica_estagio',
    'projeto_ambiental', 'ggbr', 'integra_edu',
]
EQUIPE_INSERCAO = ['NATÁLIA', 'PEDRO', 'STÉFANYE', 'LUCAS', 'JUNIOR', 'FELIPE']
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'inova-carreira-secret-2024')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_PERMANENT'] = True
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///inova.db')
if _db_url.startswith('postgres://'):
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ─── MODELS ────────────────────────────────────────────────────────────────────

class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(20), default='viewer')  # admin, editor, viewer
    permissoes   = db.Column(db.Text, default='{}')  # JSON com permissoes especificas
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def get_perm(self, key):
        if self.role == 'admin':
            return True
        try:
            p = json.loads(self.permissoes or '{}')
        except:
            p = {}
        return p.get(key, False)

    def _p(self):
        try:
            return json.loads(self.permissoes or '{}')
        except:
            return {}

    def can_edit(self):
        return self.role in ('admin', 'editor') or self.get_perm('cursos_editar')

    def can_delete(self):
        return self.role == 'admin' or self.get_perm('cursos_excluir')

    def can_manage_cupons(self):
        if self.role == 'admin': return True
        if self._p().get('block_cupons'): return False
        return self.role == 'editor' or self._p().get('cupons_gerenciar', False)

    def can_manage_reembolsos(self):
        if self.role == 'admin': return True
        if self._p().get('block_reembolsos'): return False
        return self.role == 'editor' or self._p().get('reembolsos_gerenciar', False)

    def can_view_historico(self):
        if self.role == 'admin': return True
        if self._p().get('block_historico'): return False
        return self.role == 'editor' or self._p().get('historico_ver', False)

    def can_manage_usuarios(self):
        return self.role == 'admin' or self.get_perm('usuarios_gerenciar')

    def can_manage_backup(self):
        return self.role == 'admin' or self.get_perm('backup_gerenciar')

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
    insersor      = db.Column(db.Text)  # pode ser comma-separated para múltiplos insersores
    obs           = db.Column(db.Text)
    status        = db.Column(db.String(30), default='ativo')  # ativo, descontinuado, em_edicao, oculto
    cupom         = db.Column(db.String(100))
    dono          = db.Column(db.Text)        # para cursos terceiros
    ano           = db.Column(db.String(10))  # ano de criação/edição do curso
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
    cod_moodle    = db.Column(db.String(50))
    titulacao     = db.Column(db.String(50))
    plataforma_ok = db.Column(db.Boolean, default=False)
    plataforma_em = db.Column(db.DateTime)

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
    data_solicitacao = db.Column(db.Date)   # Solicitação do aluno
    valor            = db.Column(db.Float)
    valor_estorno    = db.Column(db.Float)
    nome_curso       = db.Column(db.String(300))
    categoria        = db.Column(db.String(100))
    solicitacao_1    = db.Column(db.Date)   # 1ª Solicitação (Nathy)
    solicitacao_2    = db.Column(db.Date)   # 2ª Solicitação (Jorge)
    data_aprovacao   = db.Column(db.Date)
    motivo           = db.Column(db.Text)
    curso_excluido   = db.Column(db.Date)   # Data exclusão do curso
    obs              = db.Column(db.Text)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def pendencia(self):
        """Retorna o estágio pendente atual do reembolso."""
        if not self.solicitacao_1:
            return ('sem_solic1', 'Aguarda 1ª Solicitação')
        if not self.solicitacao_2:
            return ('sem_solic2', 'Aguarda 2ª Solicitação')
        if not self.data_aprovacao:
            return ('sem_aprovacao', 'Aguarda Aprovação')
        if not self.curso_excluido:
            return ('sem_exclusao', 'Aguarda Exclusão do Curso')
        return ('concluido', 'Concluído')

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

def perm_check(check_fn_name):
    """Decorator que verifica uma permissão específica via método do User model."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            u = User.query.get(session['user_id'])
            if not u or not getattr(u, check_fn_name)():
                flash('Você não tem permissão para acessar esta seção.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

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

@app.context_processor
def inject_notificacoes():
    if 'user_id' not in session:
        return {}
    u = User.query.get(session['user_id'])
    if not u:
        return {}
    # Disciplinas pendentes (plataforma_ok=False) em cursos atribuídos a este usuário
    q = db.session.query(Discipline, Course)\
        .join(Course, Discipline.course_id == Course.id)\
        .filter(Discipline.plataforma_ok == False)\
        .filter(Course.status.notin_(['descontinuado']))\
        .filter(Course.insersor != None, Course.insersor != '')
    if u.role != 'admin':
        from sqlalchemy import or_ as sql_or, func as sql_func
        un = u.username.lower()
        q = q.filter(sql_or(
            sql_func.lower(Course.insersor) == un,
            sql_func.lower(Course.insersor).like(f'{un},%'),
            sql_func.lower(Course.insersor).like(f'%,{un}'),
            sql_func.lower(Course.insersor).like(f'%,{un},%'),
        ))
    pendentes = q.order_by(Course.nome, Discipline.ordem).all()

    by_course = {}
    for disc, curso in pendentes:
        if curso.id not in by_course:
            by_course[curso.id] = {'course': curso, 'discs': [], 'total': 0}
        by_course[curso.id]['discs'].append(disc)
        by_course[curso.id]['total'] += 1

    notif_list = sorted(by_course.values(), key=lambda x: x['total'], reverse=True)[:8]

    # Para admin: cursos marcados como finalizado aguardando publicação
    admin_finalizado = []
    if u.role == 'admin':
        admin_finalizado = Course.query.filter_by(status='finalizado')\
            .order_by(Course.updated_at.desc()).limit(15).all()

    return {
        'notif_count': len(pendentes),
        'notif_list': notif_list,
        'admin_finalizado': admin_finalizado,
        'admin_finalizado_count': len(admin_finalizado),
        'can_cupons': u.can_manage_cupons(),
        'can_reembolsos': u.can_manage_reembolsos(),
        'can_historico': u.can_view_historico(),
    }

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
            session.permanent = True
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
    filtro_ins = request.args.get('insersor', '')
    q_base = Course.query
    if filtro_ins:
        from sqlalchemy import or_ as sql_or, func as sql_func
        fi = filtro_ins.lower()
        q_base = q_base.filter(sql_or(
            sql_func.lower(Course.insersor) == fi,
            sql_func.lower(Course.insersor).like(f'{fi},%'),
            sql_func.lower(Course.insersor).like(f'%,{fi}'),
            sql_func.lower(Course.insersor).like(f'%,{fi},%'),
        ))

    total     = q_base.count()
    ativos    = q_base.filter_by(status='ativo').count()
    em_edicao = q_base.filter_by(status='em_edicao').count()
    desc      = q_base.filter_by(status='descontinuado').count()
    externos  = q_base.filter_by(status='externo').count()
    ocultos   = q_base.filter_by(status='oculto').count()
    finalizado = q_base.filter_by(status='finalizado').count()

    por_tipo  = db.session.query(Course.tipo, db.func.count(Course.id))\
                          .group_by(Course.tipo).all()
    recentes  = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    ultimo_bk = BackupRecord.query.order_by(BackupRecord.created_at.desc()).first()

    # Pendências de plataforma — apenas equipe de inserção, case-insensitive
    raw_pend = db.session.query(Course.insersor, db.func.count(Discipline.id))\
        .join(Discipline, Discipline.course_id == Course.id)\
        .filter(Discipline.plataforma_ok == False)\
        .filter(Course.insersor != None, Course.insersor != '')\
        .group_by(Course.insersor).all()
    pend_map = {nome: 0 for nome in EQUIPE_INSERCAO}
    for ins_field, qtd in raw_pend:
        for nome in ins_field.split(','):
            nome_up = nome.strip().upper()
            for canonical in EQUIPE_INSERCAO:
                if nome_up == canonical.upper():
                    pend_map[canonical] += qtd
                    break
    pend_por_ins = sorted(pend_map.items(), key=lambda x: x[1], reverse=True)

    insersores = EQUIPE_INSERCAO

    return render_template('dashboard.html',
        total=total, ativos=ativos, em_edicao=em_edicao, desc=desc,
        externos=externos, ocultos=ocultos, finalizado=finalizado,
        por_tipo=por_tipo, recentes=recentes,
        ultimo_bk=ultimo_bk, pend_por_ins=pend_por_ins,
        insersores=insersores, filtro_ins=filtro_ins)

# ─── COURSES ───────────────────────────────────────────────────────────────────

@app.route('/cursos')
@login_required
def cursos():
    tipo     = request.args.get('tipo','')
    area     = request.args.get('area','')
    status   = request.args.get('status','')
    busca    = request.args.get('q','')
    insersor = request.args.get('insersor','')
    lista = _build_cursos_query(tipo, area, status, busca, insersor)
    areas  = AREAS_VALIDAS
    insersores = [u.username for u in User.query.order_by(User.username).all()]
    return render_template('cursos.html', cursos=lista, areas=areas, insersores=insersores,
                           filtro_tipo=tipo, filtro_area=area, filtro_status=status,
                           filtro_insersor=insersor, busca=busca)

def _build_cursos_query(tipo, area, status, busca, insersor):
    from sqlalchemy import or_ as sql_or, func as sql_func
    q = Course.query
    if tipo:     q = q.filter_by(tipo=tipo)
    if area:     q = q.filter_by(area=area)
    if status:   q = q.filter_by(status=status)
    if insersor:
        ins = insersor.lower()
        q = q.filter(sql_or(
            sql_func.lower(Course.insersor) == ins,
            sql_func.lower(Course.insersor).like(f'{ins},%'),
            sql_func.lower(Course.insersor).like(f'%,{ins}'),
            sql_func.lower(Course.insersor).like(f'%,{ins},%'),
        ))
    if busca:    q = q.filter(Course.nome.ilike(f'%{busca}%'))
    return q.order_by(Course.nome).all()

@app.route('/cursos/exportar-excel')
@login_required
def cursos_exportar_excel():
    import openpyxl, re
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    tipo     = request.args.get('tipo','')
    area     = request.args.get('area','')
    status   = request.args.get('status','')
    busca    = request.args.get('q','')
    insersor = request.args.get('insersor','')
    lista = _build_cursos_query(tipo, area, status, busca, insersor)

    TIPO_LABELS = {
        'pos':'Pós-Graduação','profissionalizante':'Profissionalizante','rapido':'Rápido',
        'pacote':'Pacote','terceiros':'Terceiros','evento':'Evento',
        'pratica_conectada':'Prática Conectada','pratica_estagio':'Prática Estágio',
        'projeto_ambiental':'Proj. Ambiental','ggbr':'GGBR','integra_edu':'Integra Edu',
    }

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Cursos'

    thin  = Side(style='thin', color='CBD5E1')
    bdr   = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap  = Alignment(wrap_text=True, vertical='top')
    center = Alignment(horizontal='center', vertical='center')
    hfill = PatternFill('solid', fgColor='6366F1')
    hfont = Font(bold=True, color='FFFFFF', size=10)

    STATUS_COLORS = {
        'ativo':'DCFCE7','em_edicao':'FEF9C3','descontinuado':'F1F5F9',
        'oculto':'EDE9FE','finalizado':'DBEAFE','externo':'FFEDD5',
    }

    headers = ['Nome do Curso','Tipo','Área','Status','CH','Duração','Valor (R$)',
               'Insersor','Cupom','Ano','Dono/Professor','Link Venda','Obs']
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.fill = hfill; c.font = hfont; c.alignment = center; c.border = bdr
    ws.row_dimensions[1].height = 28

    for i, curso in enumerate(lista, 2):
        sc = STATUS_COLORS.get(curso.status, 'FFFFFF')
        row_fill = PatternFill('solid', fgColor=sc)
        vals = [
            curso.nome,
            TIPO_LABELS.get(curso.tipo, curso.tipo),
            curso.area or '',
            curso.status.replace('_',' ').title(),
            curso.horas or '',
            curso.meses or '',
            curso.valor or '',
            curso.insersor or '',
            curso.cupom or '',
            curso.ano or '',
            curso.dono or '',
            curso.link_venda or '',
            curso.obs or '',
        ]
        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.border = bdr; cell.alignment = wrap; cell.fill = row_fill

    widths = [55,18,12,14,8,10,10,20,14,6,18,45,30]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'

    buf = io.BytesIO()
    wb.save(buf); buf.seek(0)
    from datetime import datetime as dt
    fname = f'cursos_inova_{dt.now().strftime("%Y%m%d_%H%M")}.xlsx'
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=fname)

@app.route('/cursos/relatorio')
@login_required
def cursos_relatorio():
    tipo     = request.args.get('tipo','')
    area     = request.args.get('area','')
    status   = request.args.get('status','')
    busca    = request.args.get('q','')
    insersor = request.args.get('insersor','')
    lista = _build_cursos_query(tipo, area, status, busca, insersor)
    insersores = [u.username for u in User.query.order_by(User.username).all()]
    return render_template('cursos_relatorio.html', cursos=lista,
                           filtro_tipo=tipo, filtro_area=area, filtro_status=status,
                           filtro_insersor=insersor, busca=busca,
                           areas=AREAS_VALIDAS, insersores=insersores,
                           now=datetime.utcnow())

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
            link_imagem=d.get('link_imagem',''), insersor=','.join(d.getlist('insersores')) or session['username'],
            obs=d.get('obs',''), status=d.get('status','em_edicao'),
            ano=d.get('ano',''), cupom=d.get('cupom',''), dono=d.get('dono',''),
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
    usuarios = User.query.order_by(User.username).all()
    return render_template('curso_form.html', curso=None, tipos=TIPOS_CURSO, areas=AREAS_VALIDAS, usuarios=usuarios)

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
        novo_status = d.get('status', c.status)
        # Somente admin pode publicar (ativo); colaboradores podem marcar como finalizado no máximo
        if novo_status == 'ativo' and session.get('role') != 'admin':
            novo_status = c.status
        c.status = novo_status
        c.cupom=d.get('cupom','')
        c.dono=d.get('dono',''); c.ano=d.get('ano',''); c.updated_at=datetime.utcnow()
        ins_list = d.getlist('insersores')
        if ins_list: c.insersor = ','.join(ins_list)
        # Update disciplines — preserva plataforma_ok/plataforma_em por nome da disciplina
        if d.get('disciplinas_json') is not None:
            discs_novas = json.loads(d.get('disciplinas_json','[]') or '[]')
            # Mapa: nome normalizado → disciplina existente (para preservar status da plataforma)
            existentes = {ex.nome.strip().lower(): ex
                         for ex in Discipline.query.filter_by(course_id=id).all()}
            Discipline.query.filter_by(course_id=id).delete()
            for i, disc in enumerate(discs_novas):
                nome = disc.get('nome','')
                anterior = existentes.get(nome.strip().lower())
                dd = Discipline(
                    course_id=id,
                    modulo=disc.get('modulo',''),
                    ordem=i+1,
                    nome=nome,
                    carga=disc.get('carga',''),
                    professor=disc.get('professor',''),
                    cod_moodle=disc.get('cod_moodle',''),
                    titulacao=disc.get('titulacao',''),
                    plataforma_ok=anterior.plataforma_ok if anterior else False,
                    plataforma_em=anterior.plataforma_em if anterior else None
                )
                db.session.add(dd)
        db.session.commit()
        log_action(session['user_id'], session['username'], 'editar', 'course', id, f'{old_nome} → {c.nome}')
        flash('Curso atualizado!', 'success')
        if d.get('from_page') == 'matrizes':
            return redirect(url_for('matrizes'))
        return redirect(url_for('curso_detalhe', id=id))
    disc = Discipline.query.filter_by(course_id=id).order_by(Discipline.ordem).all()
    tipos = ['pos','profissionalizante','rapido','pacote','terceiros','evento','pratica_conectada','pratica_estagio','projeto_ambiental','ggbr','integra_edu']
    usuarios = User.query.order_by(User.username).all()
    return render_template('curso_form.html', curso=c, disc=disc, tipos=TIPOS_CURSO, areas=AREAS_VALIDAS, usuarios=usuarios)

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
@perm_check('can_manage_cupons')
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
@perm_check('can_manage_reembolsos')
def reembolsos():
    busca      = request.args.get('q', '').strip()
    f_colab    = request.args.get('colab', '').strip()
    f_cat      = request.args.get('categoria', '').strip()
    f_pend     = request.args.get('pendencia', '').strip()

    q = Refund.query
    if busca:
        q = q.filter(db.or_(
            Refund.nome_aluno.ilike(f'%{busca}%'),
            Refund.nome_curso.ilike(f'%{busca}%')
        ))
    if f_colab:
        q = q.filter(Refund.colab.ilike(f'%{f_colab}%'))
    if f_cat:
        q = q.filter(Refund.categoria.ilike(f'%{f_cat}%'))

    items = q.order_by(Refund.created_at.desc()).all()

    # Filtro por pendência (feito em Python pois usa property)
    if f_pend:
        items = [r for r in items if r.pendencia[0] == f_pend]

    contagem = {'sem_solic1': 0, 'sem_solic2': 0, 'sem_aprovacao': 0, 'sem_exclusao': 0, 'concluido': 0}
    for r in Refund.query.all():
        contagem[r.pendencia[0]] += 1

    colabs = sorted({r.colab for r in Refund.query.all() if r.colab})
    cats   = sorted({r.categoria for r in Refund.query.all() if r.categoria})

    return render_template('reembolsos.html', items=items, contagem=contagem,
                           busca=busca, f_colab=f_colab, f_cat=f_cat, f_pend=f_pend,
                           colabs=colabs, cats=cats)

@app.route('/reembolsos/novo', methods=['GET','POST'])
@editor_required
def reembolso_novo():
    if request.method == 'POST':
        r = _refund_from_form(request.form)
        db.session.add(r)
        db.session.commit()
        log_action(session['user_id'], session['username'], 'criar', 'reembolso', r.id, r.nome_aluno)
        flash('Reembolso registrado!', 'success')
        return redirect(url_for('reembolsos'))
    return render_template('reembolso_form.html', item=None)

@app.route('/reembolsos/<int:id>/editar', methods=['GET','POST'])
@editor_required
def reembolso_editar(id):
    r = Refund.query.get_or_404(id)
    if request.method == 'POST':
        d = request.form
        def pdate(s):
            try: return datetime.strptime(s, '%Y-%m-%d').date()
            except: return None
        r.colab          = d.get('colab','')
        r.nome_aluno     = d.get('nome_aluno','')
        r.nome_curso     = d.get('nome_curso','')
        r.categoria      = d.get('categoria','')
        r.data_compra    = pdate(d.get('data_compra',''))
        r.data_solicitacao = pdate(d.get('data_solicitacao',''))
        r.valor          = float(d.get('valor',0) or 0)
        r.valor_estorno  = float(d.get('valor_estorno',0) or 0)
        r.solicitacao_1  = pdate(d.get('solicitacao_1',''))
        r.solicitacao_2  = pdate(d.get('solicitacao_2',''))
        r.data_aprovacao = pdate(d.get('data_aprovacao',''))
        r.motivo         = d.get('motivo','')
        r.curso_excluido = pdate(d.get('curso_excluido',''))
        r.obs            = d.get('obs','')
        db.session.commit()
        log_action(session['user_id'], session['username'], 'editar', 'reembolso', id, r.nome_aluno)
        flash('Reembolso atualizado!', 'success')
        return redirect(url_for('reembolsos'))
    return render_template('reembolso_form.html', item=r)

@app.route('/reembolsos/<int:id>/excluir', methods=['POST'])
@admin_required
def reembolso_excluir(id):
    r = Refund.query.get_or_404(id)
    nome = r.nome_aluno
    db.session.delete(r)
    db.session.commit()
    log_action(session['user_id'], session['username'], 'excluir', 'reembolso', id, nome)
    flash(f'Reembolso de "{nome}" excluído.', 'success')
    return redirect(url_for('reembolsos'))

def _refund_from_form(d):
    def pdate(s):
        try: return datetime.strptime(s, '%Y-%m-%d').date()
        except: return None
    return Refund(
        colab=d.get('colab',''), nome_aluno=d.get('nome_aluno',''),
        nome_curso=d.get('nome_curso',''), categoria=d.get('categoria',''),
        data_compra=pdate(d.get('data_compra','')),
        data_solicitacao=pdate(d.get('data_solicitacao','')),
        valor=float(d.get('valor',0) or 0),
        valor_estorno=float(d.get('valor_estorno',0) or 0),
        solicitacao_1=pdate(d.get('solicitacao_1','')),
        solicitacao_2=pdate(d.get('solicitacao_2','')),
        data_aprovacao=pdate(d.get('data_aprovacao','')),
        motivo=d.get('motivo',''),
        curso_excluido=pdate(d.get('curso_excluido','')),
        obs=d.get('obs','')
    )

# ─── MATRIZES CURRICULARES ─────────────────────────────────────────────────────

@app.route('/disciplina/<int:disc_id>/toggle', methods=['POST'])
@login_required
def disciplina_toggle(disc_id):
    d = Discipline.query.get_or_404(disc_id)
    d.plataforma_ok = not d.plataforma_ok
    d.plataforma_em = datetime.utcnow() if d.plataforma_ok else None
    db.session.commit()
    return jsonify({'ok': d.plataforma_ok, 'disc_id': disc_id})

@app.route('/curso/<int:course_id>/disciplinas/marcar-todas', methods=['POST'])
@login_required
def disciplinas_marcar_todas(course_id):
    marcar = request.json.get('marcar', True)
    discs = Discipline.query.filter_by(course_id=course_id).all()
    now = datetime.utcnow()
    for d in discs:
        d.plataforma_ok = marcar
        d.plataforma_em = now if marcar else None
    db.session.commit()
    return jsonify({'ok': True, 'total': len(discs), 'marcar': marcar})

@app.route('/matrizes')
@login_required
def matrizes():
    busca = request.args.get('q', '').strip()
    filtro_tipo = request.args.get('tipo', '')
    filtro_insersor = request.args.get('insersor', '').strip()
    filtro_pendente = request.args.get('pendente', '')

    # Apenas cursos que têm pelo menos uma disciplina
    from sqlalchemy import exists as sql_exists, or_
    q = Course.query.filter(
        sql_exists().where(Discipline.course_id == Course.id)
    )
    if filtro_tipo:
        q = q.filter_by(tipo=filtro_tipo)
    todos = q.order_by(Course.tipo, Course.nome).all()

    # Filtrar por busca (nome do curso OU nome da disciplina)
    if busca:
        busca_low = busca.lower()
        disc_cids = {r[0] for r in db.session.query(Discipline.course_id)
                     .filter(Discipline.nome.ilike(f'%{busca}%')).all()}
        todos = [c for c in todos if busca_low in c.nome.lower() or c.id in disc_cids]

    # Filtrar por insersor (campo pode ser comma-separated)
    if filtro_insersor:
        fi_low = filtro_insersor.lower()
        todos = [c for c in todos if c.insersor and
                 any(fi_low == p.strip().lower() for p in c.insersor.split(','))]

    def _parse_ch(val):
        if not val:
            return 0
        import re
        m = re.search(r'\d+', str(val))
        return int(m.group()) if m else 0

    course_data = []
    for c in todos:
        discs = Discipline.query.filter_by(course_id=c.id).order_by(Discipline.ordem).all()
        if busca and busca.lower() not in c.nome.lower():
            discs = [d for d in discs if busca.lower() in d.nome.lower()]
        total_ch = sum(_parse_ch(d.carga) for d in discs)
        ok_count = sum(1 for d in discs if d.plataforma_ok)
        course_data.append({'course': c, 'disciplines': discs, 'total_ch': total_ch, 'ok_count': ok_count})

    # Filtrar apenas pendentes (alguma disciplina não concluída)
    if filtro_pendente == '1':
        course_data = [item for item in course_data
                       if item['ok_count'] < len(item['disciplines'])]

    tipos_disponiveis = [r[0] for r in db.session.query(Course.tipo).join(
        Discipline, Discipline.course_id == Course.id).distinct().all()]

    # Lista de insersores para o filtro (expandindo comma-separated)
    ins_set = set()
    for c in Course.query.filter(
        sql_exists().where(Discipline.course_id == Course.id)
    ).all():
        if c.insersor:
            for p in c.insersor.split(','):
                p = p.strip()
                if p:
                    ins_set.add(p)
    insersores_disponiveis = sorted(ins_set)

    total_pendentes = sum(1 for item in course_data
                          if item['ok_count'] < len(item['disciplines']))

    # Pendentes por tipo (apenas cursos com disciplinas, sem filtro atual)
    todos_para_chips = Course.query.filter(
        sql_exists().where(Discipline.course_id == Course.id)
    ).all()
    pendentes_por_tipo = {}
    for c in todos_para_chips:
        discs_c = Discipline.query.filter_by(course_id=c.id).all()
        ok_c = sum(1 for d in discs_c if d.plataforma_ok)
        if ok_c < len(discs_c):
            pendentes_por_tipo[c.tipo] = pendentes_por_tipo.get(c.tipo, 0) + 1

    return render_template('matrizes.html', course_data=course_data, busca=busca,
                           filtro_tipo=filtro_tipo, tipos_disponiveis=tipos_disponiveis,
                           filtro_insersor=filtro_insersor, filtro_pendente=filtro_pendente,
                           insersores_disponiveis=insersores_disponiveis,
                           total_pendentes=total_pendentes,
                           pendentes_por_tipo=pendentes_por_tipo)

@app.route('/matrizes/marcar-tudo', methods=['POST'])
@login_required
def matrizes_marcar_tudo():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Acesso negado'}), 403
    data = request.json or {}
    marcar = data.get('marcar', True)
    filtro_tipo = data.get('tipo', '')
    filtro_status = data.get('status', '')
    filtro_insersor = data.get('insersor', '').strip()
    now = datetime.utcnow()
    q = Course.query
    if filtro_tipo:
        q = q.filter_by(tipo=filtro_tipo)
    if filtro_status:
        q = q.filter_by(status=filtro_status)
    cursos = q.all()
    if filtro_insersor:
        fi_low = filtro_insersor.lower()
        cursos = [c for c in cursos if c.insersor and
                  any(fi_low == p.strip().lower() for p in c.insersor.split(','))]
    course_ids = [c.id for c in cursos]
    discs = Discipline.query.filter(Discipline.course_id.in_(course_ids)).all()
    for d in discs:
        d.plataforma_ok = marcar
        d.plataforma_em = now if marcar else None
    db.session.commit()
    parts = []
    if filtro_tipo: parts.append(f'tipo={filtro_tipo}')
    if filtro_status: parts.append(f'status={filtro_status}')
    if filtro_insersor: parts.append(f'insersor={filtro_insersor}')
    filtro_desc = ' (' + ', '.join(parts) + ')' if parts else ' (todos)'
    log_action(session['user_id'], session['username'],
               'marcar_tudo' if marcar else 'desmarcar_tudo',
               'discipline', None,
               f'{"Marcou" if marcar else "Desmarcou"} {len(discs)} disciplinas{filtro_desc}')
    return jsonify({'ok': True, 'total': len(discs), 'marcar': marcar})

@app.route('/matrizes/relatorio')
@login_required
def matrizes_relatorio():
    filtro_tipo = request.args.get('tipo', '')
    filtro_status = request.args.get('status', '')
    from sqlalchemy import exists as sql_exists
    import re
    q = Course.query.filter(sql_exists().where(Discipline.course_id == Course.id))
    if filtro_tipo:
        q = q.filter_by(tipo=filtro_tipo)
    if filtro_status:
        q = q.filter_by(status=filtro_status)
    todos = q.order_by(Course.tipo, Course.nome).all()

    def _parse_ch(val):
        if not val: return 0
        m = re.search(r'\d+', str(val))
        return int(m.group()) if m else 0

    course_data = []
    for c in todos:
        discs = Discipline.query.filter_by(course_id=c.id).order_by(Discipline.ordem).all()
        total_ch = sum(_parse_ch(d.carga) for d in discs)
        course_data.append({'course': c, 'disciplines': discs, 'total_ch': total_ch})

    tipos_disponiveis = [r[0] for r in db.session.query(Course.tipo).join(
        Discipline, Discipline.course_id == Course.id).distinct().all()]
    status_list = ['ativo', 'em_edicao', 'finalizado', 'descontinuado', 'oculto']

    return render_template('matrizes_relatorio.html', course_data=course_data,
                           filtro_tipo=filtro_tipo, filtro_status=filtro_status,
                           tipos_disponiveis=tipos_disponiveis, status_list=status_list,
                           now=datetime.utcnow())

@app.route('/matrizes/exportar-excel')
@login_required
def matrizes_exportar_excel():
    import openpyxl, re
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from sqlalchemy import exists as sql_exists

    filtro_tipo   = request.args.get('tipo', '')
    filtro_status = request.args.get('status', '')

    q = Course.query.filter(sql_exists().where(Discipline.course_id == Course.id))
    if filtro_tipo:   q = q.filter_by(tipo=filtro_tipo)
    if filtro_status: q = q.filter_by(status=filtro_status)
    todos = q.order_by(Course.tipo, Course.nome).all()

    def _parse_ch(val):
        if not val: return 0
        m = re.search(r'\d+', str(val))
        return int(m.group()) if m else 0

    TIPO_LABELS = {
        'pos':'Pós-Graduação','profissionalizante':'Profissionalizante','rapido':'Rápido',
        'pacote':'Pacote','terceiros':'Terceiros','evento':'Evento',
        'pratica_conectada':'Prática Conectada','pratica_estagio':'Prática Estágio',
        'projeto_ambiental':'Proj. Ambiental','ggbr':'GGBR','integra_edu':'Integra Edu',
    }

    wb = openpyxl.Workbook()

    # ── Aba 1: Resumo por curso ─────────────────────────────────────────────
    ws_res = wb.active
    ws_res.title = 'Resumo'

    hdr_fill   = PatternFill('solid', fgColor='6366F1')
    hdr_font   = Font(bold=True, color='FFFFFF', size=10)
    ok_fill    = PatternFill('solid', fgColor='DCFCE7')
    pend_fill  = PatternFill('solid', fgColor='FEF9C3')
    thin       = Side(style='thin', color='CBD5E1')
    border     = Border(left=thin, right=thin, top=thin, bottom=thin)
    center     = Alignment(horizontal='center', vertical='center', wrap_text=True)
    wrap       = Alignment(wrap_text=True, vertical='top')

    res_headers = ['Curso', 'Tipo', 'Área', 'Status', 'CH Total', 'Duração',
                   'Valor (R$)', 'Insersor', 'Cupom', 'Ano', 'Link de Venda',
                   'Total Disc.', 'Na Plataforma', 'Pendentes', '% Concluído']
    for col, h in enumerate(res_headers, 1):
        c = ws_res.cell(row=1, column=col, value=h)
        c.fill = hdr_fill; c.font = hdr_font; c.alignment = center; c.border = border

    ws_res.row_dimensions[1].height = 30

    for row_idx, curso in enumerate(todos, 2):
        discs = Discipline.query.filter_by(course_id=curso.id).order_by(Discipline.ordem).all()
        total_ch  = sum(_parse_ch(d.carga) for d in discs)
        ok_count  = sum(1 for d in discs if d.plataforma_ok)
        pend      = len(discs) - ok_count
        pct       = round(ok_count / len(discs) * 100) if discs else 0
        values = [
            curso.nome,
            TIPO_LABELS.get(curso.tipo, curso.tipo),
            curso.area or '',
            curso.status.replace('_',' ').title(),
            f'{total_ch}h' if total_ch else (curso.horas or ''),
            curso.meses or '',
            curso.valor or '',
            curso.insersor or '',
            curso.cupom or '',
            curso.ano or '',
            curso.link_venda or '',
            len(discs), ok_count, pend,
            f'{pct}%',
        ]
        row_fill = ok_fill if pct == 100 else (pend_fill if pct > 0 else None)
        for col, val in enumerate(values, 1):
            cell = ws_res.cell(row=row_idx, column=col, value=val)
            cell.border = border
            cell.alignment = wrap
            if row_fill and col <= 11:
                cell.fill = row_fill

    # Column widths resumo
    widths = [50, 18, 14, 14, 10, 10, 10, 20, 12, 8, 40, 10, 12, 10, 10]
    for i, w in enumerate(widths, 1):
        ws_res.column_dimensions[get_column_letter(i)].width = w

    # Freeze header
    ws_res.freeze_panes = 'A2'

    # ── Aba 2: Matrizes completas ────────────────────────────────────────────
    ws_mat = wb.create_sheet('Matrizes')

    mat_headers = ['Curso', 'Tipo', 'Área', 'Status', 'Insersor',
                   'Módulo', '#', 'Disciplina', 'CH', 'Professor', 'Titulação',
                   'Plataforma', 'Data Inserção']
    for col, h in enumerate(mat_headers, 1):
        c = ws_mat.cell(row=1, column=col, value=h)
        c.fill = hdr_fill; c.font = hdr_font; c.alignment = center; c.border = border
    ws_mat.row_dimensions[1].height = 28

    row_idx = 2
    for curso in todos:
        discs = Discipline.query.filter_by(course_id=curso.id).order_by(Discipline.ordem).all()
        for d in discs:
            values = [
                curso.nome,
                TIPO_LABELS.get(curso.tipo, curso.tipo),
                curso.area or '',
                curso.status.replace('_',' ').title(),
                curso.insersor or '',
                d.modulo or '',
                d.ordem,
                d.nome,
                d.carga or '',
                d.professor or '',
                d.titulacao or '',
                'Sim' if d.plataforma_ok else 'Pendente',
                d.plataforma_em.strftime('%d/%m/%Y') if d.plataforma_ok and d.plataforma_em else '',
            ]
            row_fill = ok_fill if d.plataforma_ok else pend_fill
            for col, val in enumerate(values, 1):
                cell = ws_mat.cell(row=row_idx, column=col, value=val)
                cell.border = border
                cell.alignment = wrap
                cell.fill = row_fill
            row_idx += 1

    # Column widths matrizes
    mat_widths = [45, 18, 12, 14, 18, 12, 5, 45, 8, 22, 18, 10, 12]
    for i, w in enumerate(mat_widths, 1):
        ws_mat.column_dimensions[get_column_letter(i)].width = w
    ws_mat.freeze_panes = 'A2'

    # ── Salva e envia ────────────────────────────────────────────────────────
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    from datetime import datetime as dt
    ts = dt.now().strftime('%Y%m%d_%H%M')
    fname = f'matrizes_inova_{ts}.xlsx'
    return send_file(buf, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name=fname)

# ─── HISTÓRICO / AUDIT ─────────────────────────────────────────────────────────

@app.route('/historico')
@perm_check('can_view_historico')
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
            perms = _perms_from_form(request.form)
            u = User(username=d['username'], password=hash_pw(d['password']),
                     role=d['role'], permissoes=json.dumps(perms))
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
        u.permissoes = json.dumps(_perms_from_form(d))
        if d.get('password'):
            u.password = hash_pw(d['password'])
        db.session.commit()
        log_action(session['user_id'], session['username'], 'editar', 'user', id, u.username)
        flash('Usuário atualizado!', 'success')
        return redirect(url_for('usuarios'))
    return render_template('usuario_form.html', user=u)

def _perms_from_form(d):
    keys = [
        'cursos_editar', 'cursos_excluir',
        'cupons_gerenciar', 'reembolsos_gerenciar',
        'historico_ver', 'usuarios_gerenciar', 'backup_gerenciar',
        'block_cupons', 'block_reembolsos', 'block_historico',
    ]
    return {k: (d.get(f'perm_{k}') == 'on') for k in keys}

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
    if not app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
        flash('Backup de arquivo está disponível apenas no modo local. Os dados no Supabase são gerenciados na nuvem.', 'info')
        return redirect(url_for('dashboard'))
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
    if not os.path.exists(fpath):
        flash('Arquivo de backup não disponível neste ambiente.', 'warning')
        return redirect(url_for('backup_lista'))
    return send_file(fpath, as_attachment=True, download_name=rec.filename)

@app.route('/backup/lista')
@admin_required
def backup_lista():
    bks = BackupRecord.query.order_by(BackupRecord.created_at.desc()).all()
    return render_template('backups.html', bks=bks)

# ─── SEED DATA ─────────────────────────────────────────────────────────────────

def _import_excel():
    import re as _re2

    def is_numero(val):
        try: return int(str(val).strip()) > 0
        except: return False

    def limpar_horas(val):
        if val is None: return ''
        m = _re2.match(r'^(\d+\.?\d*)', str(val).strip())
        return m.group(1) if m else ''

    def limpar_valor(val):
        if val is None: return ''
        s = str(val).strip()
        return s if s not in ('-', '') else ''

    def pd(v):
        return v.date() if isinstance(v, datetime) else None

    admin = User.query.filter_by(username='admin').first()
    admin_id = admin.id if admin else None

    def ac(nome, tipo, area, horas, valor, link, link_img='', desc='', obs='', status='ativo', insersor='', meses='', cupom='', dono=''):
        if not nome or str(nome).strip() == '': return None
        c = Course(nome=str(nome).strip()[:300], tipo=tipo,
                   area=str(area or '').strip()[:100], horas=str(horas or '').strip()[:20],
                   meses=str(meses or '').strip()[:20], valor=str(valor or '').strip()[:50],
                   link_venda=str(link or '').strip(), link_imagem=str(link_img or '').strip(),
                   descricao=str(desc or '').strip(), obs=str(obs or '').strip(),
                   status=status, insersor=str(insersor or '').strip()[:100],
                   cupom=str(cupom or '').strip()[:100], dono=str(dono or '').strip(),
                   created_by=admin_id)
        db.session.add(c)
        return c

    try:
        import openpyxl
        excel_path = os.path.join(os.path.dirname(__file__), 'CURSOS INOVA - LINKS (1).xlsx')
        wb = openpyxl.load_workbook(excel_path)

        # PÓS-GRADUAÇÃO — só linhas onde col[0] é número (ignora linhas de disciplinas)
        for shname in wb.sheetnames:
            if 'MATRIZES' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=3, values_only=True):
                    if not is_numero(row[0]): continue
                    area_val = str(row[2] or '').strip()
                    if area_val.endswith('h') and area_val[:-1].isdigit(): continue
                    ac(row[1], 'pos', row[2], limpar_horas(row[3]), limpar_valor(row[5]),
                       str(row[7] or ''), obs=str(row[8] or ''), insersor=str(row[6] or ''),
                       meses=str(row[4] or ''))
                break

        # PROFISSIONALIZANTES
        for shname in wb.sheetnames:
            if 'PROFISSIONALIZANTE' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not is_numero(row[0]): continue
                    ac(row[1], 'profissionalizante', row[2], limpar_horas(row[3]), '',
                       str(row[4] or ''), link_img=str(row[6] or ''),
                       desc=str(row[5] or ''), obs=str(row[7] or ''), insersor='INOVA')
                break

        # RÁPIDOS
        for shname in wb.sheetnames:
            if 'RÁPIDOS INOVA' in shname or 'RAPIDOS INOVA' in shname:
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not is_numero(row[0]): continue
                    ac(row[1], 'rapido', row[2], limpar_horas(row[3]), limpar_valor(row[5]),
                       str(row[4] or ''), link_img=str(row[7] or ''),
                       desc=str(row[6] or ''), obs=str(row[8] or ''), insersor='INOVA')
                break

        # PACOTES
        for shname in wb.sheetnames:
            if shname.upper() == 'PACOTE CURSOS':
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not is_numero(row[0]): continue
                    ac(row[1], 'pacote', row[2], limpar_horas(row[3]), limpar_valor(row[8]),
                       str(row[4] or ''), obs=str(row[6] or ''), insersor=str(row[5] or ''))
                break

        # TERCEIROS
        for shname in wb.sheetnames:
            if 'TERCEIROS' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not is_numero(row[0]): continue
                    obs = str(row[10] or '').strip()
                    s = 'descontinuado' if 'DESCONTINUADO' in obs.upper() else 'ativo'
                    ac(row[1], 'terceiros', row[5], limpar_horas(row[3]), limpar_valor(row[2]),
                       str(row[6] or ''), desc=str(row[8] or ''), obs=obs, dono=str(row[7] or ''))
                break

        # EVENTOS
        for shname in wb.sheetnames:
            if shname.upper() == 'EVENTOS':
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[2]: continue
                    obs_ev = f"Tipo: {row[1] or ''} | Data: {row[5] or ''}" + (f" | {row[8]}" if row[8] else "")
                    ac(row[2], 'evento', 'EVENTO', limpar_horas(row[3]), limpar_valor(row[6]),
                       str(row[4] or ''), obs=obs_ev, insersor='INOVA')
                break

        # PRÁTICAS CONECTADAS
        for shname in wb.sheetnames:
            if 'CONECTADA' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[1]: continue
                    ac(row[1], 'pratica_conectada', str(row[0] or ''), '', '',
                       str(row[3] or ''), status='oculto', insersor='INOVA', cupom=str(row[2] or ''))
                break

        # PRÁTICAS ESTÁGIO
        for shname in wb.sheetnames:
            if 'ESTAGIO' in shname.upper() or 'ESTÁGIO' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[0]: continue
                    ac(row[0], 'pratica_estagio', str(row[1] or ''), '', '',
                       str(row[5] or ''), insersor=str(row[3] or ''), cupom=str(row[4] or ''))
                break

        # PROJ. AMBIENTES PROF
        for shname in wb.sheetnames:
            if 'AMBIENTES' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not is_numero(row[0]): continue
                    ac(row[1], 'projeto_ambiental', '', '', '', str(row[3] or ''),
                       status='oculto', insersor='INOVA', cupom=str(row[2] or ''), obs=str(row[4] or ''))
                break

        # GGBR
        for shname in wb.sheetnames:
            if 'GGBR' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not is_numero(row[0]): continue
                    ac(row[1], 'ggbr', str(row[2] or ''), limpar_horas(row[3]),
                       limpar_valor(row[5]), str(row[4] or ''), insersor='INOVA')
                break

        # INTEGRA EDU
        for shname in wb.sheetnames:
            if 'INTEGRA' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[0]: continue
                    ac(row[0], 'integra_edu', '', limpar_horas(row[1]), '',
                       str(row[2] or ''), obs=str(row[3] or ''), insersor='INOVA')
                break

        db.session.commit()

        # CUPONS
        for shname in wb.sheetnames:
            if shname.upper() == 'CUPOM':
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[0] or str(row[0]).strip() in ('NOME', ''): continue
                    try:
                        cp = Coupon(nome=str(row[0]).strip()[:100], quantidade=int(row[1] or 0),
                                   desconto=float(row[2] or 0), cursos_tipo=str(row[3] or '').strip(),
                                   limite_curso=int(row[4] or 1), uso_unico=(str(row[5] or '').upper()=='SIM'),
                                   data_inicial=pd(row[6]), data_final=pd(row[7]) if len(row) > 7 else None,
                                   obs=str(row[8] or '').strip() if len(row) > 8 else '')
                        db.session.add(cp)
                    except: pass
                break

        # REEMBOLSOS
        for shname in wb.sheetnames:
            if 'REEMBOLSO' in shname.upper():
                ws = wb[shname]
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if not row[1] or str(row[1]).strip() in ('NOME ALUNO', ''): continue
                    try:
                        r = Refund(colab=str(row[0] or '').strip(), nome_aluno=str(row[1] or '').strip(),
                                  data_compra=pd(row[2]), data_solicitacao=pd(row[3]),
                                  valor=float(str(row[4] or 0).replace(',', '.') or 0),
                                  valor_estorno=float(str(row[5] or 0).replace(',', '.') or 0),
                                  nome_curso=str(row[6] or '').strip(), categoria=str(row[7] or '').strip(),
                                  data_aprovacao=pd(row[10]) if len(row) > 10 else None,
                                  motivo=str(row[11] or '').strip() if len(row) > 11 else '')
                        db.session.add(r)
                    except: pass
                break

        db.session.commit()

        # ── DISCIPLINAS DAS MATRIZES (PÓS) ────────────────────────────────
        import unicodedata as _ud

        def norm_nome(s):
            s = _re2.sub(r'\s+', ' ', str(s).upper().strip())
            s = s.replace('ESP. EM ', 'ESPECIALIZAÇÃO EM ').replace('ESP.EM ', 'ESPECIALIZAÇÃO EM ')
            # Remove acentos
            s = ''.join(c for c in _ud.normalize('NFKD', s) if not _ud.combining(c))
            return _re2.sub(r'\s+', ' ', s).strip()

        def nome_sim(a, b):
            na, nb = norm_nome(a), norm_nome(b)
            for n in [30, 25, 20, 15, 10]:
                if na[:n] == nb[:n] and len(na) >= n and len(nb) >= n:
                    return True
            return False

        pos_courses = Course.query.filter_by(tipo='pos').all()

        sheet_m = next((s for s in wb.sheetnames if 'MATRIZES' in s.upper()), None)
        if sheet_m and pos_courses:
            ws_m = wb[sheet_m]
            all_rows = list(ws_m.iter_rows(min_row=3, values_only=True))

            # Encontrar onde terminam as linhas de cursos e começam as matrizes
            matrix_start = len(all_rows)
            for i, row in enumerate(all_rows):
                try: int(str(row[0] or '').strip())
                except:
                    matrix_start = i
                    break

            cur_id = None
            in_disc = False
            disc_ordem = 0
            cur_modulo = None

            for row in all_rows[matrix_start:]:
                c0 = str(row[0] or '').strip()
                c1 = str(row[1] or '').strip()
                c2 = str(row[2] or '').strip()
                c3 = str(row[3] or '').strip()

                if not c0 and not c1 and not c2 and not c3:
                    in_disc = False
                    continue

                if c1.upper() == 'DISCIPLINAS':
                    in_disc = True
                    disc_ordem = 0
                    cur_modulo = None
                    continue

                if not c0 and not c1 and c2:
                    continue

                if not c2:
                    cname = c0 if (c0 and not c1) else c1
                    if cname and cname.upper() not in ('PROFESSOR', 'PROFESSORES', 'DISCIPLINAS'):
                        in_disc = False
                        disc_ordem = 0
                        cur_modulo = None
                        cur_id = None
                        match = next((c for c in pos_courses if nome_sim(c.nome, cname)), None)
                        if match:
                            existing = Discipline.query.filter_by(course_id=match.id).count()
                            cur_id = match.id if existing == 0 else None
                    continue

                if in_disc and c1 and c2 and cur_id:
                    if c0 and not c0.isdigit():
                        cur_modulo = c0
                        disc_ordem += 1
                    elif c0 and c0.isdigit():
                        disc_ordem = int(c0)
                    else:
                        disc_ordem += 1
                    db.session.add(Discipline(
                        course_id=cur_id, modulo=cur_modulo,
                        ordem=disc_ordem, nome=c1, carga=c2 or None,
                        professor=c3 or None
                    ))

            db.session.commit()

        print("[OK] Dados importados com sucesso!")
    except FileNotFoundError:
        print("[INFO] Arquivo Excel nao encontrado.")
        db.session.rollback()
    except Exception as e:
        print(f"[ERRO] Ao importar Excel: {e}")
        db.session.rollback()

def seed_data():
    if User.query.count() == 0:
        admin = User(username='admin', password=hash_pw('inova2024'), role='admin')
        junior = User(username='junior', password=hash_pw('inova2024'), role='editor')
        felipe = User(username='felipe', password=hash_pw('inova2024'), role='editor')
        viewer = User(username='visualizador', password=hash_pw('inova2024'), role='viewer')
        db.session.add_all([admin, junior, felipe, viewer])
        db.session.commit()
    if Course.query.count() == 0:
        _import_excel()

@app.route('/admin/reimportar', methods=['GET', 'POST'])
@admin_required
def admin_reimportar():
    Discipline.query.delete()
    Course.query.delete()
    Coupon.query.delete()
    Refund.query.delete()
    db.session.commit()
    _import_excel()
    flash('Dados limpos e reimportados com sucesso!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin/excel-debug')
@admin_required
def admin_excel_debug():
    import openpyxl, os
    excel_path = os.path.join(os.path.dirname(__file__), 'CURSOS INOVA - LINKS (1).xlsx')
    wb = openpyxl.load_workbook(excel_path)
    linhas = [f"<b>Abas:</b> {', '.join(wb.sheetnames)}<br><br>"]

    # Linhas 40-70 do Profissionalizantes (após os cursos numerados)
    for shname in wb.sheetnames:
        if 'PROFISSIONALIZANTE' in shname.upper():
            linhas.append(f"<b>Aba: {shname} (linhas 40-70)</b><br>")
            ws = wb[shname]
            for i, row in enumerate(ws.iter_rows(min_row=40, max_row=70, values_only=True)):
                cols = [str(c or '')[:35] for c in row[:6]]
                linhas.append(f"Linha {i+40}: {' | '.join(cols)}<br>")
            break

    linhas.append("<br>")

    # Aba DISCIPLINAS PÓS
    if 'DISCIPLINAS PÓS' in wb.sheetnames:
        linhas.append("<b>Aba: DISCIPLINAS PÓS (primeiras 20 linhas)</b><br>")
        ws = wb['DISCIPLINAS PÓS']
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=20, values_only=True)):
            cols = [str(c or '')[:35] for c in row[:8]]
            linhas.append(f"Linha {i+1}: {' | '.join(cols)}<br>")

    return ''.join(linhas)

@app.route('/admin/status')
@admin_required
def admin_status():
    from sqlalchemy import func
    linhas = [f"<b>Status do banco:</b><br>"]
    linhas.append(f"Cursos: {Course.query.count()}<br>")
    linhas.append(f"Disciplinas: {Discipline.query.count()}<br>")
    linhas.append(f"Cupons: {Coupon.query.count()}<br>")
    linhas.append(f"Reembolsos: {Refund.query.count()}<br><br>")
    linhas.append("<b>Cursos por tipo:</b><br>")
    for tipo, qtd in db.session.query(Course.tipo, func.count(Course.id)).group_by(Course.tipo).all():
        com_disc = db.session.query(func.count(Course.id)).filter(
            Course.tipo == tipo,
            db.session.query(Discipline).filter(Discipline.course_id == Course.id).exists()
        ).scalar()
        linhas.append(f"{tipo}: {qtd} cursos, {com_disc} com disciplinas<br>")
    return ''.join(linhas)

# ─── INIT ──────────────────────────────────────────────────────────────────────

_db_ready = False

@app.before_request
def ensure_db():
    global _db_ready
    if not _db_ready:
        try:
            db.create_all()
            seed_data()
            _db_ready = True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"<pre>Erro ao inicializar banco:\n{traceback.format_exc()}</pre>", 500

if __name__ == '__main__':
    t = threading.Thread(target=backup_scheduler, daemon=True)
    t.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

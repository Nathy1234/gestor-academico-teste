"""
Script de migracao: exporta dados do SQLite local e importa no PostgreSQL do Render.

Como usar:
  1. Rode localmente com o DATABASE_URL do Render:
     $env:DATABASE_URL = "postgresql://usuario:senha@host/banco"
     python migrar_para_render.py
"""
import os, sys, json, hashlib
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if not DATABASE_URL:
    print("ERRO: defina a variavel DATABASE_URL com a URL do PostgreSQL do Render.")
    print('Exemplo: $env:DATABASE_URL = "postgresql://user:pass@host/db"')
    sys.exit(1)

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# --- lê o SQLite local ---
import sqlite3
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'inova.db')
if not os.path.exists(SQLITE_PATH):
    print(f"ERRO: banco SQLite nao encontrado em {SQLITE_PATH}")
    sys.exit(1)

conn_sq = sqlite3.connect(SQLITE_PATH)
conn_sq.row_factory = sqlite3.Row

def fetch(table):
    return [dict(r) for r in conn_sq.execute(f'SELECT * FROM "{table}"').fetchall()]

print("Lendo dados do SQLite...")
users      = fetch('user')
courses    = fetch('course')
disciplines = fetch('discipline')
audit_logs = fetch('audit_log')
coupons    = fetch('coupon')
refunds    = fetch('refund')
backups    = fetch('backup_record')
conn_sq.close()

print(f"  {len(users)} usuários | {len(courses)} cursos | {len(disciplines)} disciplinas")
print(f"  {len(coupons)} cupons | {len(refunds)} reembolsos | {len(audit_logs)} logs")

# --- conecta no PostgreSQL ---
import psycopg2
from psycopg2.extras import execute_values

print("\nConectando ao PostgreSQL do Render...")
conn_pg = psycopg2.connect(DATABASE_URL)
cur = conn_pg.cursor()

# Cria as tabelas via SQLAlchemy para garantir o schema correto
print("Criando tabelas no PostgreSQL...")
os.environ['DATABASE_URL'] = DATABASE_URL
from app import app, db
with app.app_context():
    db.create_all()
print("Tabelas criadas.")

def d(val, field=''):
    """Converte string de data para objeto date/datetime, ou retorna None."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val)
        except:
            return None
    if isinstance(val, str):
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(val, fmt)
            except:
                pass
    return None

def da(val):
    """Converte para date (apenas a parte da data)."""
    dt = d(val)
    return dt.date() if dt else None

# --- insere usuários ---
print("Inserindo usuários...")
cur.execute('DELETE FROM "user" CASCADE')
for u in users:
    cur.execute(
        'INSERT INTO "user" (id, username, password, role, permissoes, created_at) VALUES (%s,%s,%s,%s,%s,%s)',
        (u['id'], u['username'], u['password'], u['role'],
         u.get('permissoes', '{}'), d(u.get('created_at')) or datetime.utcnow())
    )

# --- insere cursos ---
print("Inserindo cursos...")
cur.execute('DELETE FROM course CASCADE')
for c in courses:
    cur.execute(
        '''INSERT INTO course
           (id, nome, tipo, area, horas, meses, valor, link_venda, descricao,
            link_imagem, insersor, obs, status, cupom, dono, ano, extra_data,
            created_at, updated_at, created_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (c['id'], c['nome'], c.get('tipo'), c.get('area'), c.get('horas'),
         c.get('meses'), c.get('valor'), c.get('link_venda'), c.get('descricao'),
         c.get('link_imagem'), c.get('insersor'), c.get('obs'), c.get('status','ativo'),
         c.get('cupom'), c.get('dono'), c.get('ano'), c.get('extra_data'),
         d(c.get('created_at')) or datetime.utcnow(),
         d(c.get('updated_at')) or datetime.utcnow(),
         c.get('created_by'))
    )

# --- insere disciplinas ---
print("Inserindo disciplinas...")
cur.execute('DELETE FROM discipline')
for disc in disciplines:
    plat_ok = bool(disc.get('plataforma_ok', 0))
    cur.execute(
        '''INSERT INTO discipline
           (id, course_id, modulo, ordem, nome, carga, professor,
            cod_moodle, titulacao, plataforma_ok, plataforma_em)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (disc['id'], disc['course_id'], disc.get('modulo'), disc.get('ordem'),
         disc['nome'], disc.get('carga'), disc.get('professor'),
         disc.get('cod_moodle'), disc.get('titulacao'),
         plat_ok, d(disc.get('plataforma_em')))
    )

# --- insere cupons ---
print("Inserindo cupons...")
cur.execute('DELETE FROM coupon')
for cp in coupons:
    cur.execute(
        '''INSERT INTO coupon
           (id, nome, quantidade, desconto, cursos_tipo, limite_curso,
            uso_unico, data_inicial, data_final, obs, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (cp['id'], cp['nome'], cp.get('quantidade'), cp.get('desconto'),
         cp.get('cursos_tipo'), cp.get('limite_curso'), bool(cp.get('uso_unico',1)),
         da(cp.get('data_inicial')), da(cp.get('data_final')),
         cp.get('obs'), d(cp.get('created_at')) or datetime.utcnow())
    )

# --- insere reembolsos ---
print("Inserindo reembolsos...")
cur.execute('DELETE FROM refund')
for r in refunds:
    cur.execute(
        '''INSERT INTO refund
           (id, colab, nome_aluno, data_compra, data_solicitacao, valor, valor_estorno,
            nome_curso, categoria, solicitacao_1, solicitacao_2, data_aprovacao,
            motivo, curso_excluido, obs, created_at)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (r['id'], r.get('colab'), r.get('nome_aluno'),
         da(r.get('data_compra')), da(r.get('data_solicitacao')),
         r.get('valor', 0), r.get('valor_estorno', 0),
         r.get('nome_curso'), r.get('categoria'),
         da(r.get('solicitacao_1')), da(r.get('solicitacao_2')),
         da(r.get('data_aprovacao')), r.get('motivo'),
         da(r.get('curso_excluido')), r.get('obs'),
         d(r.get('created_at')) or datetime.utcnow())
    )

# --- insere logs de auditoria ---
print("Inserindo logs de auditoria...")
cur.execute('DELETE FROM audit_log')
for lg in audit_logs:
    cur.execute(
        '''INSERT INTO audit_log
           (id, user_id, username, action, entity, entity_id, detail, timestamp)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',
        (lg['id'], lg.get('user_id'), lg.get('username'), lg.get('action'),
         lg.get('entity'), lg.get('entity_id'), lg.get('detail'),
         d(lg.get('timestamp')) or datetime.utcnow())
    )

# Atualiza as sequences do PostgreSQL para não conflitar com IDs existentes
for table, col in [('user','id'),('course','id'),('discipline','id'),
                   ('coupon','id'),('refund','id'),('audit_log','id')]:
    cur.execute(f"SELECT setval(pg_get_serial_sequence('\"{table}\"','{col}'), COALESCE((SELECT MAX({col}) FROM \"{table}\"),1))")

conn_pg.commit()
cur.close()
conn_pg.close()

print("\nMigracao concluida com sucesso!")
print("Todos os dados foram copiados para o PostgreSQL do Render.")

import sys
sys.path.insert(0, '.')
from app import app, db, Discipline
from datetime import datetime

with app.app_context():
    now = datetime.utcnow()
    total = Discipline.query.filter_by(plataforma_ok=False).count()
    Discipline.query.filter_by(plataforma_ok=False).update({'plataforma_ok': True, 'plataforma_em': now})
    db.session.commit()
    print(f'Marcou {total} disciplinas como concluidas.')
    print(f'Total no banco: {Discipline.query.count()} disciplinas')

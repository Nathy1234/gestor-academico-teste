import sys
sys.path.insert(0, '.')
from app import app, db, Course, Discipline

with app.app_context():
    # Ver quais profissionalizantes tem disciplinas e quais sao
    prof_com_disc = Course.query.filter_by(tipo='profissionalizante').all()
    print('=== PROFISSIONALIZANTES COM DISCIPLINAS ===')
    for c in prof_com_disc:
        discs = Discipline.query.filter_by(course_id=c.id).all()
        if discs:
            print(f'\n{c.nome[:60]}:')
            for d in discs[:3]:
                print(f'  - {d.nome[:50]} ({d.carga})')
            if len(discs) > 3:
                print(f'  ... +{len(discs)-3} mais')

    print('\n=== POS SEM DISCIPLINAS ===')
    from sqlalchemy import exists as sql_exists
    pos_sem = Course.query.filter_by(tipo='pos').filter(
        ~sql_exists().where(Discipline.course_id == Course.id)
    ).all()
    for c in pos_sem:
        print(f'  - {c.nome[:70]}')

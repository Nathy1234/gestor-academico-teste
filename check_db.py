import sys
sys.path.insert(0, '.')
from app import app, db, Course, Discipline

with app.app_context():
    total_cursos = Course.query.count()
    total_disc = Discipline.query.count()
    disc_ok = Discipline.query.filter_by(plataforma_ok=True).count()

    pos_com_disc = db.session.query(Course.id).filter_by(tipo='pos').join(
        Discipline, Discipline.course_id == Course.id).distinct().count()
    pos_total = Course.query.filter_by(tipo='pos').count()

    prof_com_disc = db.session.query(Course.id).filter_by(tipo='profissionalizante').join(
        Discipline, Discipline.course_id == Course.id).distinct().count()
    prof_total = Course.query.filter_by(tipo='profissionalizante').count()

    externos = Course.query.filter_by(status='externo').count()

    print(f'Cursos total: {total_cursos}')
    print(f'Disciplinas total: {total_disc} ({disc_ok} concluidas)')
    print(f'Pos com disciplinas: {pos_com_disc}/{pos_total}')
    print(f'Profissionalizantes com disciplinas: {prof_com_disc}/{prof_total}')
    print(f'Cursos com status=externo: {externos}')

    print()
    print('=== Cursos POS sem disciplinas ===')
    from sqlalchemy import exists as sql_exists
    pos_sem_disc = Course.query.filter_by(tipo='pos').filter(
        ~sql_exists().where(Discipline.course_id == Course.id)
    ).all()
    for c in pos_sem_disc:
        print(f'  - {c.nome[:60]}')

import sys, getpass
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from alembic.config import Config
from alembic import command
from sqlalchemy import select
from backend.argus.config import settings
from backend.argus.db import SessionLocal, User, Role, AIModel, audit
from backend.argus.security import passwords, ROLES
command.upgrade(Config('alembic.ini'),'head')
with SessionLocal() as db:
    for name,permissions in ROLES.items():
        if not db.scalar(select(Role).where(Role.name==name)): db.add(Role(name=name,permissions=permissions))
    if not db.scalar(select(AIModel)):
        db.add(AIModel(name="YOLO11 nano",version="COCO / Ultralytics v8.3.0",filename=Path(settings.model_path).name,state="ACTIVE"))
    db.commit()
    if db.scalar(select(User).where(User.username==settings.admin_username)):
        print('Database migrated; existing administrator retained.')
    else:
        password=settings.admin_password or getpass.getpass('New administrator password (12+ characters): ')
        if len(password)<12: raise SystemExit('Password must have at least 12 characters')
        db.add(User(username=settings.admin_username,password=passwords.hash(password),role='Administrator'))
        audit(db,'setup','administrator_created',settings.admin_username);db.commit()
        print('Database ready. Administrator:',settings.admin_username)

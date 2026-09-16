import os,tempfile
from pathlib import Path
ROOT=Path(tempfile.mkdtemp(prefix='argus-tests-'))
# ARGUS_TEST_DATABASE_URL runs the suite on a disposable PostgreSQL database; tables are dropped per test.
os.environ['DATABASE_URL']=os.environ.get('ARGUS_TEST_DATABASE_URL') or 'sqlite:///'+str(ROOT/'test.db')
os.environ['STORAGE_DIR']=str(ROOT/'storage')
os.environ['ADMIN_PASSWORD']='test-admin-password'
os.environ['MPLCONFIGDIR']=str(ROOT/'mpl')
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'yolo')
import pytest
from fastapi.testclient import TestClient
from backend.argus.db import Base,engine,SessionLocal,User
from backend.argus.security import passwords
from backend.argus.main import app
@pytest.fixture
def client():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add(User(username='admin',password=passwords.hash('test-admin-password'),role='Administrator'));db.commit()
    with TestClient(app) as c:
        c.headers['X-Argus-Request']='1'
        assert c.post('/api/auth/login',json={'username':'admin','password':'test-admin-password'}).status_code==200
        yield c

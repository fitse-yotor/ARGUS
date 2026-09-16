import hashlib, secrets, time
from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import select
from .db import User, Session, Role, get_db

passwords = PasswordHash.recommended()
ROLES = {
 'Administrator': ['read','operate','configure','review','incident','admin','audit'],
 'Operator': ['read','operate','configure','review','incident'],
 'Incident Controller': ['read','review','incident'],
 'Supervisor': ['read','review','incident','audit'],
 'Investigator': ['read'], 'Auditor': ['read','audit'],
}

def current_user(request: Request, db=Depends(get_db)):
    token=request.cookies.get('argus_session','')
    session=db.scalar(select(Session).where(Session.token_hash==hashlib.sha256(token.encode()).hexdigest(),Session.expires>time.time()))
    user=db.get(User,session.user_id) if session else None
    if not user or not user.enabled: raise HTTPException(401,'Authentication required')
    if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('x-argus-request') != '1':
        raise HTTPException(403,'Missing request protection header')
    if request.method in ('GET','HEAD') and request.url.path!='/api/auth/me' and 'read' not in permissions_for(db,user):
        raise HTTPException(403,'Role does not permit reading operational data')
    return user

def permissions_for(db, user):
    role=db.scalar(select(Role).where(Role.name==user.role))
    return role.permissions if role else ROLES.get(user.role,[])

def permit(permission):
    def dependency(user=Depends(current_user), db=Depends(get_db)):
        if permission not in permissions_for(db,user): raise HTTPException(403,'Role does not permit this action')
        return user
    return dependency

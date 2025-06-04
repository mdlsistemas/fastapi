from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Path, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict
import os

import crud, schemas, auth
from database import SessionLocal, engine, Base
from models import Movimiento
from datetime import datetime, timedelta

# Crear las tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta media para fotos de perfil y productos
if not os.path.exists("media"):
    os.makedirs("media")
app.mount("/media", StaticFiles(directory="media"), name="media")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === LOGIN ===
@app.post("/login")
def login(datos: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    usuario = crud.get_usuario_by_email(db, datos.email)
    if not usuario or not auth.verificar_password(datos.password, usuario.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = auth.crear_token({
        "sub": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "foto": usuario.foto
    })
    return {"token": token}

# === PERFIL DEL USUARIO AUTENTICADO ===
@app.get("/usuarios/me", response_model=schemas.UsuarioOut)
def leer_mi_perfil(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = auth.decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    usuario = crud.get_usuario_by_email(db, payload.get("sub"))
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario

# === CRUD USUARIOS ===

@app.post("/usuarios", response_model=schemas.UsuarioOut)
def crear_usuario(user: schemas.UsuarioCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear usuarios")
    if crud.get_usuario_by_email(db, user.email):
        raise HTTPException(status_code=409, detail="Email ya registrado")
    nuevo_usuario = crud.crear_usuario(db, user.nombre, user.email, user.password, user.rol, user.foto)
    return nuevo_usuario

@app.post("/usuarios/upload", response_model=schemas.UsuarioOut)
def crear_usuario_upload(
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rol: str = Form(...),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear usuarios")
    foto_url = None
    if foto:
        extension = foto.filename.split(".")[-1].lower()
        filename = f"{email.replace('@','_')}_foto.{extension}"
        save_path = f"media/{filename}"
        with open(save_path, "wb") as buffer:
            buffer.write(foto.file.read())
        foto_url = save_path
    if crud.get_usuario_by_email(db, email):
        raise HTTPException(status_code=409, detail="Email ya registrado")
    nuevo_usuario = crud.crear_usuario(db, nombre, email, password, rol, foto_url)
    return nuevo_usuario

@app.get("/usuarios", response_model=List[schemas.UsuarioOut])
def listar_usuarios(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Sólo los administradores pueden ver usuarios")
    return crud.listar_usuarios(db)

@app.put("/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
def actualizar_usuario(
    usuario_id: int = Path(..., gt=0),
    nombre: str = Form(...),
    email: str = Form(...),
    rol: str = Form(...),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar usuarios")
    usuario = crud.get_usuario_by_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    foto_url = usuario.foto
    if foto:
        extension = foto.filename.split(".")[-1].lower()
        filename = f"{email.replace('@','_')}_foto.{extension}"
        save_path = f"media/{filename}"
        with open(save_path, "wb") as buffer:
            buffer.write(foto.file.read())
        foto_url = save_path
    usuario = crud.actualizar_usuario(db, usuario_id, nombre, email, rol, foto_url)
    return usuario

@app.put("/usuarios/{usuario_id}/clave")
def cambiar_clave_usuario(
    usuario_id: int = Path(..., gt=0),
    nueva_clave: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    usuario = crud.get_usuario_by_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="No autorizado para cambiar esta clave")
    from auth import hash_password
    usuario.password = hash_password(nueva_clave)
    db.commit()
    return {"msg": "Clave actualizada correctamente"}

@app.delete("/usuarios/{usuario_id}")
def eliminar_usuario(
    usuario_id: int = Path(..., gt=0),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar usuarios")
    usuario = crud.get_usuario_by_id(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(usuario)
    db.commit()
    return {"msg": "Usuario eliminado correctamente"}

# ===================== PRODUCTOS =====================

@app.post("/productos", response_model=schemas.ProductoOut)
def crear_producto(
    product_name: str = Form(...),
    sku: str = Form(""),
    unit_of_measure: str = Form(""),
    cost: float = Form(0),
    sale_price: float = Form(0),
    category: str = Form(""),
    location: str = Form(""),
    active: str = Form("Yes"),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear productos")
    product_id = crud.generar_product_id(db)
    foto_url = None
    if foto:
        extension = foto.filename.split(".")[-1].lower()
        filename = f"{product_id}_foto.{extension}"
        save_path = f"media/{filename}"
        with open(save_path, "wb") as buffer:
            buffer.write(foto.file.read())
        foto_url = save_path
    nuevo = crud.crear_producto(db, product_id, product_name, sku, unit_of_measure, cost, sale_price, category, location, active, foto_url)
    return nuevo

@app.get("/productos")
def listar_productos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = auth.decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    productos = crud.listar_productos(db)
    lista = []
    for prod in productos:
        prod_dict = prod.__dict__.copy()
        prod_dict['stock'] = crud.calcular_stock(db, prod.product_id)
        prod_dict.pop('_sa_instance_state', None)
        lista.append(prod_dict)
    return lista

@app.get("/productos/{product_id}")
def get_producto(product_id: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = auth.decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    prod = crud.get_producto_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    prod_dict = prod.__dict__.copy()
    prod_dict['stock'] = crud.calcular_stock(db, product_id)
    prod_dict.pop('_sa_instance_state', None)
    return prod_dict

@app.put("/productos/{product_id}", response_model=schemas.ProductoOut)
def actualizar_producto(
    product_id: str,
    product_name: str = Form(...),
    sku: str = Form(""),
    unit_of_measure: str = Form(""),
    cost: float = Form(0),
    sale_price: float = Form(0),
    category: str = Form(""),
    location: str = Form(""),
    active: str = Form("Yes"),
    foto: UploadFile = File(None),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar productos")
    prod = crud.get_producto_by_id(db, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    foto_url = prod.foto
    if foto:
        extension = foto.filename.split(".")[-1].lower()
        filename = f"{product_id}_foto.{extension}"
        save_path = f"media/{filename}"
        with open(save_path, "wb") as buffer:
            buffer.write(foto.file.read())
        foto_url = save_path
    return crud.actualizar_producto(db, product_id, product_name, sku, unit_of_measure, cost, sale_price, category, location, active, foto_url)

@app.delete("/productos/{product_id}")
def eliminar_producto(product_id: str, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    payload = auth.decodificar_token(token)
    if not payload or payload.get("rol") != "administrador":
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar productos")
    ok = crud.eliminar_producto(db, product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"msg": "Producto eliminado correctamente"}

# ========== MOVIMIENTOS DE STOCK ==========

@app.post("/movimientos", response_model=schemas.MovimientoOut)
def registrar_movimiento(
    datos: schemas.MovimientoCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    return crud.crear_movimiento(db, datos.product_id, datos.movement_type, datos.quantity, datos.notes)

@app.get("/movimientos", response_model=List[schemas.MovimientoOut])
def listar_movimientos(
    product_id: str = None,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    return crud.listar_movimientos(db, product_id)

# ========== PREDICCION DE STOCK ==========

@app.get("/prediccion_stock")
def prediccion_stock(
    dias: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    payload = auth.decodificar_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")

    # USAR productos con stock calculado
    productos = crud.listar_productos_con_stock(db)
    resultado = []

    from datetime import datetime, timedelta

    for prod in productos:
        # prod es un dict {'product_id': ..., 'stock': ..., etc}
        product_id = prod['product_id']
        stock = prod['stock']
        product_name = prod.get('product_name', '')

        fecha_inicio = datetime.now() - timedelta(days=dias)
        # Traer solo movimientos "Venta" o "Egreso" de este producto en X días
        movimientos = db.query(Movimiento).filter(
            Movimiento.product_id == product_id,
            Movimiento.date >= fecha_inicio,
            ((Movimiento.notes == "Venta") | (Movimiento.movement_type == "Egreso"))
        ).all()

        cantidad_total = sum(abs(m.quantity) for m in movimientos if m.quantity and (m.notes == "Venta" or m.movement_type == "Egreso"))
        consumo_diario = cantidad_total / dias if dias > 0 else 0
        dias_restantes = stock / consumo_diario if consumo_diario > 0 else float('inf')

        resultado.append({
            "product_id": product_id,
            "product_name": product_name,
            "stock": stock,
            "consumo_diario": round(consumo_diario, 2),
            "dias_restantes": round(dias_restantes, 1) if dias_restantes != float('inf') else "∞"
        })

    return resultado

@app.get("/")
def read_root():
    return {"status": "OK", "mensaje": "API de gestión de stock funcionando"}

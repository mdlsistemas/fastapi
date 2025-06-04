from sqlalchemy.orm import Session
from models import Usuario, UserRole, Producto, Movimiento
from auth import hash_password
from sqlalchemy import func
from datetime import datetime

# ---------- USUARIOS ----------

def get_usuario_by_email(db: Session, email: str):
    return db.query(Usuario).filter(Usuario.email == email).first()

def crear_usuario(db: Session, nombre, email, password, rol, foto=None):
    user = Usuario(
        nombre=nombre,
        email=email,
        password=hash_password(password),
        rol=rol,
        foto=foto
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_usuario_by_id(db: Session, usuario_id: int):
    return db.query(Usuario).filter(Usuario.id == usuario_id).first()

def listar_usuarios(db: Session):
    return db.query(Usuario).all()

def actualizar_usuario(db: Session, usuario_id: int, nombre, email, rol, foto_url):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if usuario:
        usuario.nombre = nombre
        usuario.email = email
        usuario.rol = rol
        usuario.foto = foto_url
        db.commit()
        db.refresh(usuario)
    return usuario

# ---------- PRODUCTOS ----------

def generar_product_id(db: Session):
    last = db.query(Producto).order_by(Producto.product_id.desc()).first()
    if last and last.product_id[0] == "P":
        num = int(last.product_id[1:]) + 1
    else:
        num = 1
    return f"P{num:03d}"

def crear_producto(db: Session, product_id, product_name, sku, unit_of_measure, cost, sale_price, category, location, active, foto):
    prod = Producto(
        product_id=product_id,
        product_name=product_name,
        sku=sku,
        unit_of_measure=unit_of_measure,
        cost=cost,
        sale_price=sale_price,
        category=category,
        location=location,
        active=active,
        foto=foto
    )
    db.add(prod)
    db.commit()
    db.refresh(prod)
    return prod

def listar_productos(db: Session):
    return db.query(Producto).all()

def get_producto_by_id(db: Session, product_id: str):
    return db.query(Producto).filter(Producto.product_id == product_id).first()

def actualizar_producto(db: Session, product_id, product_name, sku, unit_of_measure, cost, sale_price, category, location, active, foto_url):
    prod = db.query(Producto).filter(Producto.product_id == product_id).first()
    if prod:
        prod.product_name = product_name
        prod.sku = sku
        prod.unit_of_measure = unit_of_measure
        prod.cost = cost
        prod.sale_price = sale_price
        prod.category = category
        prod.location = location
        prod.active = active
        prod.foto = foto_url
        db.commit()
        db.refresh(prod)
    return prod

def eliminar_producto(db: Session, product_id: str):
    prod = db.query(Producto).filter(Producto.product_id == product_id).first()
    if prod:
        db.delete(prod)
        db.commit()
        return True
    return False

# ---------- STOCK Y MOVIMIENTOS ----------

def calcular_stock(db: Session, product_id: str):
    # Suma ingresos (movement_type=Ingreso o notes=Compra), resta egresos (movement_type=Egreso o notes=Venta)
    ingresos = db.query(func.coalesce(func.sum(Movimiento.quantity), 0)).filter(
        Movimiento.product_id == product_id,
        ((Movimiento.movement_type.ilike('Ingreso')) | (Movimiento.notes.ilike('Compra')))
    ).scalar()
    egresos = db.query(func.coalesce(func.sum(Movimiento.quantity), 0)).filter(
        Movimiento.product_id == product_id,
        ((Movimiento.movement_type.ilike('Egreso')) | (Movimiento.notes.ilike('Venta')))
    ).scalar()
    return int(ingresos or 0) - int(egresos or 0)

def listar_productos_con_stock(db: Session):
    productos = db.query(Producto).all()
    result = []
    for prod in productos:
        stock = calcular_stock(db, prod.product_id)
        prod_dict = prod.__dict__.copy()
        prod_dict['stock'] = stock
        prod_dict.pop('_sa_instance_state', None)
        result.append(prod_dict)
    return result

def generar_movement_id(db):
    last = db.query(Movimiento).order_by(Movimiento.movement_id.desc()).first()
    if last and last.movement_id[0] == "M":
        num = int(last.movement_id[1:]) + 1
    else:
        num = 1
    return f"M{num:03d}"

def crear_movimiento(db, product_id, tipo, cantidad, descripcion):
    movement_id = generar_movement_id(db)
    mov = Movimiento(
        movement_id=movement_id,
        date=datetime.now(),
        product_id=product_id,
        movement_type=tipo,
        quantity=cantidad,
        order_id=None,
        notes=descripcion,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov

def listar_movimientos(db, product_id=None):
    q = db.query(Movimiento)
    if product_id:
        q = q.filter(Movimiento.product_id == product_id)
    return q.order_by(Movimiento.date.desc()).all()

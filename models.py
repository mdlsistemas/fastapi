from sqlalchemy import Column, Integer, String, Enum, DateTime, func, DECIMAL, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base
import enum

# --- Enum de roles de usuario ---
class UserRole(str, enum.Enum):
    administrador = "administrador"
    operador = "operador"
    analista = "analista"

# --- Usuario ---
class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    rol = Column(Enum(UserRole), default=UserRole.operador)
    foto = Column(String(255), nullable=True)
    fecha_registro = Column(DateTime, server_default=func.now())

# --- Producto (Product Master Data) ---
class Producto(Base):
    __tablename__ = "productos"
    product_id = Column(String(10), primary_key=True, index=True)
    product_name = Column(String(100), nullable=False)
    sku = Column(String(50))
    unit_of_measure = Column(String(20))
    cost = Column(DECIMAL(10,2))
    sale_price = Column(DECIMAL(10,2))
    category = Column(String(50))
    location = Column(String(50))
    active = Column(String(5), default='Yes')
    foto = Column(String(255))
    movimientos = relationship("Movimiento", back_populates="producto")

# --- Movimiento (Inventory Movement Data) ---
class Movimiento(Base):
    __tablename__ = "movimientos"
    movement_id = Column(String(10), primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    product_id = Column(String(10), ForeignKey('productos.product_id'))
    movement_type = Column(String(30))  # INBOUND, OUTBOUND, etc.
    quantity = Column(Integer)
    order_id = Column(String(20))
    notes = Column(Text)
    producto = relationship("Producto", back_populates="movimientos")

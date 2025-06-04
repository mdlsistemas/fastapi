from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

MYSQL_URL = "mysql+pymysql://root:root@localhost:3306/gestion_de_stock"

engine = create_engine(MYSQL_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


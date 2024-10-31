from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from settings import settings


engine = create_engine(f'postgresql://{settings.db.postgres_user}:{settings.db.postgres_password}'
                       f'@{settings.db.postgres_host}:{settings.db.postgres_port}/{settings.db.postgres_db}')

Session = sessionmaker(
    engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


def create_db():
    Base.metadata.create_all(engine)
    print('Database created')
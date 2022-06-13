import logging
import time

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions

from collector_app.configs import database as config

Base = declarative_base()

assert config.DB_CONNECTION_STRING, 'Connection string is empty'
engine = create_engine(config.DB_CONNECTION_STRING, echo=config.DB_ECHO, future=True)

logger = logging.getLogger(__name__)


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True)
    departure_date = Column(Date, nullable=False)
    departure_station_id = Column(Integer, nullable=False)
    arrival_station_id = Column(Integer, nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)

    collected_data = relationship("CollectedData", back_populates='config',)
    collected_data_raw = relationship("CollectedDataRaw", back_populates='config',)

    def __repr__(self):
        return f"Config(id={self.id!r})"


class CollectedData(Base):
    __tablename__ = "collected_data"
    id = Column(Integer, primary_key=True)
    train_number = Column(String, nullable=False)
    tickets_json = Column(JSONB, nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False, server_default=functions.now())
    config_id = Column(Integer, ForeignKey("config.id"), nullable=False)

    config = relationship("Config", back_populates='collected_data',)

    def __repr__(self):
        return f"CollectedData(id={self.id!r})"


class CollectedDataRaw(Base):
    __tablename__ = "collected_data_raw"
    id = Column(Integer, primary_key=True)
    raw_data = Column(JSONB, nullable=False)
    collected_at = Column(DateTime(timezone=True), nullable=False, server_default=functions.now())
    config_id = Column(Integer, ForeignKey("config.id"), nullable=False)

    config = relationship("Config", back_populates='collected_data_raw',)

    def __repr__(self):
        return f"CollectedDataRaw(id={self.id!r})"


def create_all():
    print('[WARNING] About to DROP and then create all tables...')
    for i in range(5, 0, -1):
        print(f'{i}...')
        time.sleep(1)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print('Done!')


if __name__ == "__main__":
    import datetime
    from sqlalchemy.orm import Session

    create_all()
    with Session(engine) as session:
        session.add_all([
            Config(
                departure_date=datetime.date.today(),
                departure_station_id=2000000,
                arrival_station_id=2004000,
                enabled=True,
            )
        ])
        session.commit()

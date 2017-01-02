from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

engine = create_engine('sqlite:///ibrest.db', convert_unicode=True)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

# ---------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------
class FilledOrders(Base):
    __tablename__ = 'filled_orders'
    id = Column(Integer, primary_key=True)
    ib_id = Column(Integer)
    order_status = Column(String)

    def __init__(self, ib_id=None, order_status=None):
        self.ib_id = ib_id
        self.order_status = order_status

    def __repr__(self):
        return '<IB OrderID {}>'.format(self.ib_id)



def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    Base.metadata.create_all(bind=engine)
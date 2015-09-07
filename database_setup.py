"""
database_setup.py: Using SQLAlchemy, sets up configuration, classes, tables,
and mappers; creating empty DB for use in application.py.
"""
__author__ = "Rick Ertl"

# CONFIGURATION - PART 1
# Import SQLAlchemy required classes
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import backref

Base = declarative_base()

# CLASSES, TABLES & MAPPERS
# Define class for admin users
class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))


# Define class for parent category of items
class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'id': self.id,
        }


# Define class for items under each category
class Item(Base):
    __tablename__ = 'item'

    name = Column(String(80), nullable=False)
    id = Column(Integer, primary_key=True)
    description = Column(String(250))
    image = Column(String(100))
    price = Column(String(8))
    category_id = Column(Integer, ForeignKey('category.id'))
    # Added cascade to ensure child items are deleted with category delete
    category = relationship(Category,
                            backref=backref("categories",
                                            cascade="all, delete-orphan"))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'name': self.name,
            'description': self.description,
            'id': self.id,
            'image': self.image,
            'price': self.price,
        }

# CONFIGURATION - PART 2
engine = create_engine('sqlite:///duckies.db')

Base.metadata.create_all(engine)

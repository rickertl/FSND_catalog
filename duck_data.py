from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User

engine = create_engine('sqlite:///duckies.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Create dummy user
User1 = User(name="Rick Ertl", email="ertl.rick@gmail.com",
             picture='https://lh6.googleusercontent.com/-glE6YE1fBWQ/AAAAAA'
                     'AAAAI/AAAAAAAAABI/ywdGalrRiCc/photo.jpg')
session.add(User1)
session.commit()

# Traditional Category
category1 = Category(user_id=1, name="Traditional Duckies")

session.add(category1)
session.commit()

# Add Traditional Items
Item1 = Item(user_id=1, name="Mini Rubber Ducks",
             description="One dozen mini rubber ducks.",
             image="/uploads/mini-rubber-ducks.jpg",
             price="2.99", category=category1)

session.add(Item1)
session.commit()

Item2 = Item(user_id=1, name="Classic Rubber Duck",
             description="Classic little rubber ducky bath time toy.",
             image="/uploads/rubber-duckie.jpg",
             price="4.99", category=category1)

session.add(Item2)
session.commit()

# Keychains Category
category2 = Category(user_id=1, name="Keychains")

session.add(category2)
session.commit()

# Add Keychain Items
Item1 = Item(user_id=1, name="Classic Rubber Duck Keychains",
             description="One dozen rubber duck keychains.",
             image="/uploads/basic-keychain.jpg",
             price="6.99", category=category2)

session.add(Item1)
session.commit()

Item2 = Item(user_id=1, name="Pirate Rubber Duck Keychains",
             description="One dozen rubber duck in pirate disguises"
                         " keychains.",
             image="/uploads/pirate-keychain.jpg",
             price="7.99", category=category2)

session.add(Item2)
session.commit()

# Inflatables Category
category3 = Category(user_id=1, name="Inflatables")

session.add(category3)
session.commit()

# Add Inflatable Items
Item1 = Item(user_id=1, name="Giant Ducky Inflatable",
             description="A full 60 inches long by 48 inches tall inflatable"
                         " rubber duck.",
             image="/uploads/giant-inflatable.jpg",
             price="29.99", category=category3)

session.add(Item1)
session.commit()

Item2 = Item(user_id=1, name="Clear Rubber Duck Beachball",
             description="Inflatable 16 inch clear beach ball with"
                         " yellow duck insert.",
             image="/uploads/beach-ball.jpg",
             price="7.99", category=category3)

session.add(Item2)
session.commit()

print "added rubber duck items!"

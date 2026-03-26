from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Item(db.Model):
    __tablename__ = "items"

    id    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name  = db.Column(db.String(200), nullable=False)
    value = db.Column(db.String(500), nullable=False, default="")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "value": self.value}

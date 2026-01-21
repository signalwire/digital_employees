from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    reservation_number = db.Column(db.String(6), unique=True, nullable=False)  # 6-digit random number
    name = db.Column(db.String(80), nullable=False)
    party_size = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    phone_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='confirmed')
    special_requests = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_status = db.Column(db.String(20), default='unpaid')  # 'unpaid', 'paid', 'refunded'
    payment_intent_id = db.Column(db.String(100))  # Stripe payment intent ID
    payment_amount = db.Column(db.Float)  # Total amount paid
    payment_date = db.Column(db.DateTime)  # When payment was completed
    confirmation_number = db.Column(db.String(20))  # Payment confirmation number
    payment_method = db.Column(db.String(50))  # Payment method used (e.g., 'credit_card', 'cash', 'signalwire_pay')
    orders = db.relationship('Order', backref='reservation', lazy=True)

    def to_dict(self):
        total_bill = sum(order.total_amount or 0 for order in self.orders)
        return {
            'id': self.id,
            'reservation_number': self.reservation_number,
            'name': self.name,
            'party_size': self.party_size,
            'date': self.date,
            'time': self.time,
            'phone_number': self.phone_number,
            'status': self.status,
            'special_requests': self.special_requests,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'payment_status': self.payment_status,
            'payment_intent_id': self.payment_intent_id,
            'payment_amount': self.payment_amount,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'confirmation_number': self.confirmation_number,
            'payment_method': self.payment_method,
            'orders': [order.to_dict() for order in self.orders],
            'total_bill': total_bill
        }

class Table(db.Model):
    __tablename__ = 'tables'
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, nullable=False, unique=True)
    capacity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='available')
    location = db.Column(db.String(50))
    orders = db.relationship('Order', backref='table', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'table_number': self.table_number,
            'capacity': self.capacity,
            'status': self.status,
            'location': self.location
        }

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'is_available': self.is_available
        }

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(5), unique=True, nullable=False)  # 5-digit random number
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'))
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'))
    person_name = db.Column(db.String(80))  # Name of the person for this order
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float)
    target_date = db.Column(db.String(10))  # YYYY-MM-DD when order should be ready
    target_time = db.Column(db.String(5))   # HH:MM when order should be ready
    order_type = db.Column(db.String(20))   # 'pickup' or 'delivery'
    customer_phone = db.Column(db.String(20))
    customer_address = db.Column(db.Text)   # For delivery orders
    special_instructions = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='unpaid')  # 'unpaid', 'paid', 'refunded'
    payment_intent_id = db.Column(db.String(100))  # Stripe payment intent ID
    payment_amount = db.Column(db.Float)  # Total amount paid
    payment_date = db.Column(db.DateTime)  # When payment was completed
    confirmation_number = db.Column(db.String(20))  # Payment confirmation number
    payment_method = db.Column(db.String(50))  # Payment method used (e.g., 'credit_card', 'cash', 'signalwire_pay')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'reservation_id': self.reservation_id,
            'table_id': self.table_id,
            'person_name': self.person_name,
            'status': self.status,
            'total_amount': self.total_amount,
            'target_date': self.target_date,
            'target_time': self.target_time,
            'order_type': self.order_type,
            'customer_phone': self.customer_phone,
            'customer_address': self.customer_address,
            'special_instructions': self.special_instructions,
            'payment_status': self.payment_status,
            'payment_intent_id': self.payment_intent_id,
            'payment_amount': self.payment_amount,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'confirmation_number': self.confirmation_number,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items]
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'))
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'))
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_item_id': self.menu_item_id,
            'quantity': self.quantity,
            'price_at_time': self.price_at_time,
            'notes': self.notes,
            'menu_item': self.menu_item.to_dict() if self.menu_item else None
        } 
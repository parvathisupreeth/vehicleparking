from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import or_

app = Flask(__name__)
app.secret_key = 'boosss_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking_lot.db'
db = SQLAlchemy()
db.init_app(app)
app.app_context().push()

class User(db.Model):
    __tablename__ = 'user' 
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    vehicle_number = db.Column(db.String(30), unique=True, nullable=False)

class ParkingLot(db.Model):
    __tablename__ = 'parkinglots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    landmark = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    pincode = db.Column(db.String(10))
    price = db.Column(db.Integer)
    max_spots = db.Column(db.Integer)
    places = db.relationship('Place', backref='lot', lazy=True)

class Place(db.Model):  
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parkinglots.id'))
    number = db.Column(db.Integer)
    is_reserved = db.Column(db.Boolean, default=False)

class Reservation(db.Model):
    __tablename__ = 'reservation'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'))
    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='active')
    cost_per_hour = db.Column(db.Float, nullable=True)

    user = db.relationship('User', backref='reservations')
    place = db.relationship('Place', backref='reservations')

db.create_all()


@app.route('/')
def default():
    return render_template("landing.html")


def create_auto_admin():
    if_exists = User.query.filter_by(is_admin=True).first()
    if not if_exists:
        admin = User(username='admin', password='passadmin',vehicle_number='BOSSS_HERE', is_admin=True)
        db.session.add(admin)
        db.session.commit()
        print("admin got created")
    else:
        print("admin already exists")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if not user:
            flash('User not found. Please sign up first!', 'warning')
            return redirect(url_for('signup'))

        if user.password != password:
            flash('Incorrect password!', 'error')
            return redirect(url_for('login'))

        # Valid user and password
        session['username'] = user.username
        session['user_id'] = user.id
        session['is_admin'] = user.is_admin
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'GET':
        return render_template("signup.html")
    else: 
        username = request.form.get('username')
        password = request.form.get('password')
        contact = request.form.get('contact')
        vehicle_number = request.form.get('vehicle_number')



        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists! Please login.", "warning") # You can add categories here
            return redirect(url_for('login')) # Redirect to login if user exists

        # By default, users are not admins unless assigned
        new_user = User(username=username, password=password, contact=contact, vehicle_number=vehicle_number,is_admin=False)
        db.session.add(new_user)
        db.session.commit()

        flash("Signup successful! You can now log in.", "success") 
        return redirect(url_for('login'))
    

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    user = User.query.get(session['user_id'])
    return render_template("dashboard.html", username=user.username, is_admin=user.is_admin)


@app.route('/addlot', methods=['GET', 'POST'])
def addlot():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        landmark = request.form['landmark']
        address = request.form['address']
        pincode = request.form['pincode']
        price = request.form['price']
        max_spots = int(request.form['max_spots'])

        new_lot = ParkingLot(name=name, landmark=landmark,address=address, pincode=pincode, price=price, max_spots=max_spots)
        db.session.add(new_lot)
        db.session.commit()

        # Create the spots
        for i in range(1, max_spots + 1):
            place = Place(number=i, lot_id=new_lot.id, is_reserved=False)
            db.session.add(place)
        db.session.commit()

        flash("✅ New Parking Lot Created Successfully!")
        return redirect('/dashboard')

    return render_template('addlot.html')



@app.route('/viewlots')
def viewlots():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    is_admin = user.is_admin

    search_query = request.args.get('search', '').strip()

    query = ParkingLot.query
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(or_(
            ParkingLot.name.ilike(search_pattern),
            ParkingLot.address.ilike(search_pattern),
            ParkingLot.pincode.ilike(search_pattern)
        ))

    lots = query.all()

    for lot in lots:
        lot.spots = Place.query.filter_by(lot_id=lot.id).order_by(Place.number).all()

    user_reservations = {}
    if not is_admin:
        reservations = Reservation.query.filter_by(user_id=user_id, status='active').all()
        for r in reservations:
            user_reservations[r.place_id] = True

    return render_template('viewlots.html', lots=lots, is_admin=is_admin, user_reservations=user_reservations, search=search_query)



@app.route('/reserve/<int:place_id>', methods=['POST'])
def reserve_place(place_id):
    if not session.get('user_id'):
        flash("Unauthorized access.")
        return redirect(url_for('login'))

    place = Place.query.get(place_id)
    if place and not place.is_reserved:
        place.is_reserved = True
        reservation = Reservation(user_id=session['user_id'],place_id=place.id,cost_per_hour=place.lot.price)
        db.session.add(reservation)
        db.session.commit()
        flash("Place reserved.")
    else:
        flash("Place not available.")

    return redirect(url_for('viewlots'))



@app.route('/release_place/<int:place_id>', methods=['POST'])
def release_place(place_id):
    if 'user_id' not in session:
        flash("Please log in to continue.", "danger")
        return redirect(url_for('login'))

    user_id = session['user_id']
    is_admin = session.get('is_admin', False)

    place = Place.query.get(place_id)
    reservation = Reservation.query.filter_by(place_id=place_id, status='active').first()

    if not place or not reservation:
        flash("Invalid release operation: Place or active reservation not found.", "danger")
        return redirect(url_for('viewlots'))

    # Authorization check
    if not is_admin and reservation.user_id != user_id:
        flash("You are not authorized to release this spot.", "danger")
        return redirect(url_for('viewlots'))

    now = datetime.now()
    duration_seconds = (now - reservation.start_time).total_seconds()
    total_hours = round(duration_seconds / 3600, 2)

    cost_per_hour = reservation.cost_per_hour
    if cost_per_hour is None or cost_per_hour <= 0:
        flash("Lot price is invalid!", "danger")
        return redirect(url_for('viewlots'))

    total_cost = round(total_hours * cost_per_hour, 2)

    # Update reservation and place status
    reservation.status = 'completed'
    reservation.end_time = now
    place.is_reserved = False
    reservation.cost = total_cost

    db.session.commit()

    flash(f"Spot released successfully! Total cost: ₹{reservation.cost}", "success")
    return redirect(url_for('viewlots'))





@app.route('/book/<int:lot_id>')
def book(lot_id):
    if 'user_id' not in session:
        flash("⚠️ Login required to reserve.", "danger")
        return redirect('/login')

    place = Place.query.filter_by(lot_id=lot_id, is_reserved=False).first()

    if place:
        place.is_reserved = True
        db.session.commit()

        reservation = Reservation(
            user_id=session['user_id'],
            place_id=place.id,
            start_time=datetime.now(),
            cost_per_hour=ParkingLot.query.get(lot_id).price
        )
        db.session.add(reservation)
        db.session.commit()

        flash(f"✅ Booked Place {place.number} in Lot ID {lot_id}", "success")
    else:
        flash("❌ No available places in this lot.", "warning")

    return redirect('/viewlots')



@app.route('/history')
def user_history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect('/login')  #  Force login if not authenticated

    reservations = Reservation.query.filter_by(user_id=user_id).all()
    final_data = []

    for res in reservations:
        place = Place.query.get(res.place_id)
        if not place:
            continue  # skip this reservation if place is missing

        lot = ParkingLot.query.get(place.lot_id)
        if not lot:
            continue  # skip if lot is missing

        final_data.append({
            'lot_name': lot.name,
            'place_number': place.number,
            'start_time': res.start_time,
            'end_time': res.end_time,
            'cost_per_hour': res.cost_per_hour,
            'is_active': res.status=='active'
        })

    return render_template("user_history.html", reservations=final_data)


@app.route('/editlots')
def editlots():
    if 'username' not in session or not session.get('is_admin'):
        flash("Access Denied: Admins only.")
        return redirect(url_for('login'))

    lots = ParkingLot.query.all()
    return render_template("editlots.html", lots=lots)



@app.route('/editlot/<int:lot_id>', methods=['GET', 'POST'])
def editlot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        new_name = request.form.get('lot_name')
        new_capacity = int(request.form.get('capacity'))
        new_price = int(request.form.get('price'))

        if new_capacity < 0:
            flash("Capacity can't be negative!", "danger")
            return redirect(url_for('viewlots'))

        lot.name = new_name
        lot.price = new_price

        current_spots = Place.query.filter_by(lot_id=lot.id).order_by(Place.number).all()
        current_capacity = len(current_spots)

        if new_capacity > current_capacity:
            for i in range(current_capacity + 1, new_capacity + 1):
                new_spot = Place(number=i, lot_id=lot.id, is_reserved=False)
                db.session.add(new_spot)

        elif new_capacity < current_capacity:
            removable_spots = Place.query.filter_by(lot_id=lot.id, is_reserved=False)\
                                         .order_by(Place.number.desc()).all()
            to_remove = current_capacity - new_capacity

            if len(removable_spots) < to_remove:
                flash("Cannot reduce capacity: not enough available spots.", "danger")
                return redirect(url_for('viewlots'))

            for i in range(to_remove):
                db.session.delete(removable_spots[i])

        db.session.commit()

        updated_spots = Place.query.filter_by(lot_id=lot.id).order_by(Place.number).all()
        for index, spot in enumerate(updated_spots, start=1):
            spot.number = index

        db.session.commit()
        flash("Parking Lot updated successfully!", "success")
        return redirect(url_for('viewlots'))

    return render_template('editlot.html', lot=lot)



@app.route('/deletelot/<int:lot_id>')
def deletelot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    # Check if any spot (place) in this lot is occupied
    occupied_count = Place.query.filter_by(lot_id=lot.id, is_reserved=True).count()
    if occupied_count > 0:
        flash('Cannot delete: Some spots in this lot are still occupied!', 'danger')
        return redirect(url_for('editlots'))
    db.session.delete(lot)
    db.session.commit()
    flash('Parking Lot deleted successfully!', 'success')
    return redirect(url_for('editlots'))


# 127.0.0.1(local host):5000(default for flask)


# professional admins dashboard 

@app.route('/users', methods=['GET'])
def admin_users():
    if not session.get('is_admin'):
        flash("Access Denied", "danger")
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()

    # Base query for users
    query = User.query

    # Filter if search provided (case-insensitive)
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(or_(User.username.ilike(search_pattern), User.contact.ilike(search_pattern),User.vehicle_number.ilike(search_pattern),))

    users = query.all()

    user_list = []
    for user in users:
        active_reservation = Reservation.query.filter_by(user_id=user.id, status='active').first()
        status = "Occupied" if active_reservation else "Left"

        completed_reservations = Reservation.query.filter_by(user_id=user.id, status='completed').all()
        total_seconds = 0
        for res in completed_reservations:
            if res.end_time and res.start_time:
                total_seconds += (res.end_time - res.start_time).total_seconds()
        total_hours = round(total_seconds / 3600, 2)

        user_list.append({
            'username': user.username,
            'contact': user.contact,
            'vehicle_number': user.vehicle_number,
            'status': status,
            'total_hours': total_hours
        })

    return render_template('admin_users.html', users=user_list, search=search_query)



@app.route('/analytics', methods=['GET'])
def admin_analytics():
    if not session.get('is_admin'):
        flash("Access Denied", "danger")
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').strip()

    query = ParkingLot.query
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(or_(
            ParkingLot.name.ilike(search_pattern),
            ParkingLot.address.ilike(search_pattern),
            ParkingLot.pincode.ilike(search_pattern)
        ))

    lots = query.all()

    lots_data = []
    for lot in lots:
        total_spots = lot.max_spots or 0
        occupied_spots = Place.query.filter_by(lot_id=lot.id, is_reserved=True).count() if total_spots > 0 else 0
        available_spots = total_spots - occupied_spots
        usage_percent = round((occupied_spots / total_spots) * 100, 2) if total_spots > 0 else 0

        lots_data.append({
            'id': lot.id,
            'name': lot.name,
            'location': f"{lot.address}, {lot.pincode}",
            'capacity': total_spots,
            'available': available_spots,
            'cost': lot.price,
            'occupied': occupied_spots,
            'usage_percent': usage_percent
        })

    return render_template('admin_analytics.html', lots=lots_data, search=search_query)

from flask import abort

@app.route('/admin/history')
def admin_history():
    if not session.get('is_admin'):
        flash("Access Denied: Admins only.", "danger")
        return redirect(url_for('login'))

    # Get all reservations ordered by start_time desc
    reservations = Reservation.query.order_by(Reservation.start_time.desc()).all()

    history_data = []
    for r in reservations:
        user = User.query.get(r.user_id)
        place = Place.query.get(r.place_id)
        lot = ParkingLot.query.get(place.lot_id) if place else None

        if not (user and lot and place):
            continue  # skip incomplete data

        # Calculate total time in hours (round 2 decimals)
        if r.end_time:
            duration_seconds = (r.end_time - r.start_time).total_seconds()
        else:
            # If still active, calculate duration till now
            duration_seconds = (datetime.now() - r.start_time).total_seconds()

        total_hours = round(duration_seconds / 3600, 2)

        # Calculate cost from total hours and cost_per_hour
        cost = round(total_hours * (r.cost_per_hour or 0), 2)

        history_data.append({
            'username': user.username,
            'vehicle_number': user.vehicle_number,
            'lot_name': lot.name,
            'place_number': place.number,
            'start_time': r.start_time,
            'end_time': r.end_time,
            'total_hours': total_hours,
            'cost': cost,
        })

    return render_template('admin_history.html', history=history_data)



if __name__ =='__main__':
    create_auto_admin()
    app.run(debug=True)




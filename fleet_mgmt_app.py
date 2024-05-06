from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.ext.automap import automap_base
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root@localhost/fleet_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
jwt = JWTManager(app)
db = SQLAlchemy(app)

# database models

class Account(db.Model):
  __tablename__ = 'account'
  account_id = db.Column(db.Integer, primary_key=True)
  email = db.Column(db.String(100))
  password = db.Column(db.String(100))
  zipcode = db.Column(db.String(10))
  state = db.Column(db.String(50))
  city = db.Column(db.String(50))
  street_addr = db.Column(db.String(100))
  password_hash = db.Column(db.String(128), nullable=False)
  # relationships
  drivers = db.relationship('Driver', backref='account', uselist=False)
  staff_members = db.relationship('StaffMember', backref='account', uselist=False)

  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)

class Insurance(db.Model):
  __tablename__ = 'insurance'
  insurance_id = db.Column(db.Integer, primary_key=True)
  insured_by = db.Column(db.String(100))
  expiration_date = db.Column(db.Date)
  policy_no = db.Column(db.String(50))
  vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.vehicle_id'), unique=True)
  # Define relationships
  vehicles = db.relationship('Vehicle', backref='insurance', uselist=False)

class Driver(db.Model):
  __tablename__ = 'driver'
  driver_id = db.Column(db.Integer, primary_key=True)
  license_no = db.Column(db.String(50))
  dob = db.Column(db.Date)
  first_name = db.Column(db.String(50))
  last_name = db.Column(db.String(50))
  account_id = db.Column(db.Integer, db.ForeignKey('account.account_id'), unique=True)
  # relationships
  vehicles = db.relationship('Vehicle', backref='driver', uselist=False)


class StaffMember(db.Model):
  __tablename__ = 'staff_member'
  staff_id = db.Column(db.Integer, primary_key=True)
  first_name = db.Column(db.String(50))
  last_name = db.Column(db.String(50))
  account_id = db.Column(db.Integer, db.ForeignKey('account.account_id'), unique=True)
  # relationships
  vehicles = db.relationship('Vehicle', backref='staff_member', uselist=False)

class Vehicle(db.Model):
  __tablename__ = 'vehicle'
  vehicle_id = db.Column(db.Integer, primary_key=True)
  registration_date = db.Column(db.Date)
  mileage = db.Column(db.Integer)
  make = db.Column(db.String(50))
  model = db.Column(db.String(50))
  manufacturer = db.Column(db.String(50))
  insurance_id = db.Column(db.Integer, db.ForeignKey('insurance.insurance_id'))
  driver_id = db.Column(db.Integer, db.ForeignKey('driver.driver_id'))
  record_id = db.Column(db.Integer, db.ForeignKey('maintenance_record.record_id'))
  
  # relationships
  maintenance_record = db.relationship('MaintenanceRecord', backref='vehicle', uselist=False)
  sensors = db.relationship('Sensor', backref='vehicle', uselist=False)

class Sensor(db.Model):
  __tablename__ = 'sensor'
  sensor_id = db.Column(db.Integer, primary_key=True)
  vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.vehicle_id'))
  sensor_status = db.Column(db.String(50))
  sensor_type = db.Column(db.String(50))

class MaintenanceRecord(db.Model):
  __tablename__ = 'maintenance_record'
  record_id = db.Column(db.Integer, primary_key=True)
  wiper_fluid_refilled = db.Column(db.Boolean)
  wipers_changed = db.Column(db.Boolean)
  oil_changed = db.Column(db.Boolean)
  service_date = db.Column(db.Date)
  battery_status = db.Column(db.Boolean)
  air_filter_changed = db.Column(db.Boolean)
  tires_changed = db.Column(db.Boolean)
  tires_rotated = db.Column(db.Boolean)
  brakes_replaced = db.Column(db.Boolean)
  vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.vehicle_id'))

with app.app_context():
  # get existing database tables
  Base = automap_base()
  Base.prepare(db.engine, reflect=True)

  # access existing tables
  Driver = Base.classes.driver
  StaffMember = Base.classes.staff_member
  Account = Base.classes.account
  Vehicle = Base.classes.vehicle
  MaintenanceRecord = Base.classes.maintenance_record
  Sensor = Base.classes.sensor
  Insurance = Base.classes.insurance

  # dummy routes to enable browser testing
  @app.route('/')
  def index():
    return 'Hello, World!'
  
  @app.route('/favicon.ico')
  def favicon():
    return '', 204


  # User Authentication API

  # Register a new driver
  @app.route('/register/driver', methods=['POST'])
  def register_driver():
    driver_data = request.get_json()
    new_account = Account(email=driver_data['email'], password=driver_data['password'],
                          zipcode=driver_data['zipcode'], state=driver_data['state'],
                          city=driver_data['city'], street_addr=driver_data['street_addr'])
    db.session.add(new_account)
    db.session.commit()
    new_driver = Driver(first_name=driver_data['first_name'], last_name=driver_data['last_name'],
                        license_no=driver_data['license_no'], dob=driver_data['dob'],
                        account_id=new_account.account_id)
    db.session.add(new_driver)
    db.session.commit()
    return jsonify({'message': 'Driver registered successfully'}), 201
  
  # update aaccount
  @app.route('/account/update/<int:account_id>', methods=['PUT'])
  def update_account(account_id):
    account = db.session.query(Account).get(account_id)
    if not account:
      return jsonify({'error': 'Account not found'}), 404

    update_data = request.get_json()
    account.email = update_data.get('email', account.email)
    account.password = update_data.get('password', account.password)
    account.zipcode = update_data.get('zipcode', account.zipcode)
    account.state = update_data.get('state', account.state)
    account.city = update_data.get('city', account.city)
    account.street_addr = update_data.get('street_addr', account.street_addr)

    db.session.commit()
    return jsonify({'message': 'Account updated successfully'}), 200


  # get account info
  @app.route('/account/<int:account_id>', methods=['GET'])
  def get_account(account_id):
    account = db.session.query(Account).get(account_id)
    if account:
      account_info = {'email': account.email, 'zipcode': account.zipcode, 'state': account.state,
                      'city': account.city, 'street_addr': account.street_addr}
      return jsonify(account_info), 200
    else:
      return jsonify({'error': 'Account not found'}), 404

  # get driver info
  @app.route('/driver/<int:driver_id>', methods=['GET'])
  def get_driver(driver_id):
    driver = db.session.query(Driver).get(driver_id)
    if driver:
      driver_info = {'first_name': driver.first_name, 'last_name': driver.last_name,
                      'license_no': driver.license_no, 'dob': driver.dob}
      return jsonify(driver_info), 200
    else:
      return jsonify({'error': 'Driver not found'}), 404

  # Login API (dummy implementation)
  @app.route('/login', methods=['POST'])
  def login():
    credentials = request.get_json()
    username = credentials.get('username')
    password = credentials.get('password')
    # print(username, password)

    # Perform authentication logic (e.g., check credentials against database)
    user = db.session.query(Account).filter_by(email=username).first()
    # print(user.email, user.password_hash)


    if not user.password_hash:
      user.set_password(user, password)
      db.session.commit()
    
    print(user.email, user.password_hash)
    if user and user.check_password(password):
      access_token = create_access_token(identity=username)
      return jsonify(access_token=access_token), 200
    else:
      return jsonify({'error': 'Invalid username or password'}), 401

  # Logout API (dummy implementation)
  @app.route('/logout', methods=['POST'])
  def logout():
    response = jsonify({'message': 'Logout successful'})
    unset_jwt_cookies(response)  # Clear JWT cookies from the response
    return response, 200

  # Protected route (requires JWT token)
  @app.route('/protected', methods=['GET'])
  @jwt_required()
  def protected():
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

  # Delete driver and associated account
  @app.route('/driver/delete/<int:driver_id>', methods=['DELETE'])
  def delete_driver(driver_id):
    driver = db.session.query(Driver).get(driver_id)
    if driver:
      account_id = driver.account_id
      db.session.delete(driver)
      # Also delete associated account
      account = db.session.query(Account).get(account_id)
      if account:
        db.session.delete(account)
      db.session.commit()
      return jsonify({'message': 'Driver and associated account deleted successfully'}), 200
    else:
      return jsonify({'error': 'Driver not found'}), 404
  

  # AV Fleet Management API
  @app.route('/vehicles', methods=['GET'])
  def get_vehicles():
    vehicles = db.session.query(Vehicle).all()
    vehicle_list = []
    
    for vehicle in vehicles:
      # get driver's information if driver_id is not None
      owner_info = {}
      if vehicle.driver_id:
        driver = db.session.query(Driver).filter_by(driver_id=vehicle.driver_id).first()
        if driver:
          owner_info = {
              'driver_id': driver.driver_id,
              'first_name': driver.first_name,
              'last_name': driver.last_name
          }

      vehicle_dict = {
        'id': vehicle.vehicle_id,
        'make': vehicle.make,
        'model': vehicle.model,
        'owner': owner_info
      }
      vehicle_list.append(vehicle_dict)

    return jsonify(vehicle_list), 200

  # Get vehicle information by vehicle ID
  @app.route('/vehicle/<int:vehicle_id>', methods=['GET'])
  def get_vehicle(vehicle_id):
    vehicle = db.session.query(Vehicle).filter_by(vehicle_id=vehicle_id).first()
    if vehicle:
      owner_info = None
      if vehicle.driver_id:
        driver = db.session.query(Driver).filter_by(driver_id=vehicle.driver_id).first()
        if driver:
          owner_info = {
            'driver_id': driver.driver_id,
            'first_name': driver.first_name,
            'last_name': driver.last_name
          }

      vehicle_info = {
        'make': vehicle.make,
        'model': vehicle.model,
        'owner': owner_info
      }
      return jsonify(vehicle_info), 200
    else:
      return jsonify({'error': 'Vehicle not found'}), 404

  # Register a new vehicle
  @app.route('/vehicle/register', methods=['POST'])
  def register_vehicle():
    vehicle_data = request.get_json()
    make = vehicle_data.get('make', 'Unknown Make')
    model = vehicle_data.get('model', 'Unknown Model')
    registration_date = vehicle_data.get('registration_date', )
    mileage = vehicle_data.get('mileage', None)
    manufacturer = vehicle_data.get('manufacturer', 'Unknown Manufacturer')
    insurance_id = vehicle_data.get('insurance_id', None)
    driver_id = vehicle_data.get('driver_id', None)
    num_sensors = 0 # Initialize the number of sensors to 0

    new_vehicle = Vehicle(
        make=make,
        model=model,
        registration_date=registration_date,
        mileage=mileage,
        manufacturer=manufacturer,
        insurance_id=insurance_id,
        driver_id=driver_id,
        num_sensors=num_sensors
    )

    db.session.add(new_vehicle)
    db.session.commit()

    return jsonify({'message': 'Vehicle registered successfully'}), 201
  
  # Update vehicle information
  @app.route('/vehicle/update/<int:vehicle_id>', methods=['PUT'])
  def update_vehicle(vehicle_id):
    vehicle = db.session.query(Vehicle).get(vehicle_id)
    if not vehicle:
      return jsonify({'error': 'Vehicle not found'}), 404

    update_data = request.get_json()
    vehicle.make = update_data.get('make', vehicle.make)
    vehicle.model = update_data.get('model', vehicle.model)
    vehicle.registration_date = update_data.get('registration_date', vehicle.registration_date)
    vehicle.mileage = update_data.get('mileage', vehicle.mileage)
    vehicle.manufacturer = update_data.get('manufacturer', vehicle.manufacturer)
    vehicle.insurance_id = update_data.get('insurance_id', vehicle.insurance_id)
    vehicle.driver_id = update_data.get('driver_id', vehicle.driver_id)

    db.session.commit()
    return jsonify({'message': 'Vehicle updated successfully'}), 200
  
  # Delete vehicle
  @app.route('/vehicle/delete/<int:vehicle_id>', methods=['DELETE'])
  def delete_vehicle(vehicle_id):
    vehicle = db.session.query(Vehicle).get(vehicle_id)
    if not vehicle:
      return jsonify({'error': 'Vehicle not found'}), 404

    db.session.delete(vehicle)
    db.session.commit()
    return jsonify({'message': 'Vehicle deleted successfully'}), 200


  # get all sensors
  @app.route('/sensors', methods=['GET'])
  def get_sensors():
    sensors = db.session.query(Sensor).all()
    sensor_list = [{'id': sensor.sensor_id, 'vehicle_id': sensor.vehicle_id, 'status': sensor.sensor_status, 'type': sensor.sensor_type} for sensor in sensors]
    return jsonify(sensor_list), 200

  # add sensor and associate with vehicle
  @app.route('/sensor/register', methods=['POST'])
  def register_sensor():
    sensor_data = request.get_json()
    new_sensor = Sensor(vehicle_id=sensor_data['vehicle_id'], sensor_status=sensor_data['sensor_status'], sensor_type=sensor_data['sensor_type'])
    db.session.add(new_sensor)
    db.session.commit()

    # Update the num_sensors in the vehicle table
    vehicle = db.session.query(Vehicle).filter_by(vehicle_id=sensor_data['vehicle_id']).first()
    if vehicle:
      vehicle.num_sensors = db.session.query(func.count(Sensor.vehicle_id)).filter_by(vehicle_id=sensor_data['vehicle_id']).scalar()
      db.session.commit()

    return jsonify({'message': 'Sensor registered successfully'}), 201

  # get all insurances
  @app.route('/insurances', methods=['GET'])
  def get_insurances():
    insurances = db.session.query(Insurance).all()
    insurance_list = [{'id': insurance.insurance_id, 'insured_by': insurance.insured_by, 'expiration_date': insurance.expiration_date, 'policy_no': insurance.policy_no, 'vehicle_id': insurance.vehicle_id} for insurance in insurances]
    return jsonify(insurance_list), 200
  
  # get insurance for vehicle
  @app.route('/vehicle/<int:vehicle_id>/insurance', methods=['GET'])
  def get_vehicle_insurance(vehicle_id):
    vehicle = db.session.query(Vehicle).filter_by(vehicle_id=vehicle_id).first()
    if not vehicle:
      return jsonify({'error': 'Vehicle not found'}), 404

    insurance = db.session.query(Insurance).filter_by(vehicle_id=vehicle_id).first()
    if insurance:
      insurance_info = {
        'insurance_id': insurance.insurance_id,
        'insured_by': insurance.insured_by,
        'expiration_date': insurance.expiration_date.strftime('%Y-%m-%d'),
        'policy_no': insurance.policy_no
      }
      return jsonify(insurance_info), 200
    else:
      return jsonify({'message': 'No insurance record found for this vehicle'}), 404


  # add insurance record for vehicle  
  @app.route('/insurance/register', methods=['POST'])
  def register_insurance():
    insurance_data = request.get_json()
    vehicle_id = insurance_data.get('vehicle_id')
    
    if not vehicle_id:
      return jsonify({'error': 'Vehicle ID is required'}), 400

    vehicle = db.session.query(Vehicle).filter_by(vehicle_id=vehicle_id).first()
    if not vehicle:
      return jsonify({'error': 'Vehicle not found'}), 404

    new_insurance = Insurance(insured_by=insurance_data['insured_by'],
                              expiration_date=insurance_data['expiration_date'],
                              policy_no=insurance_data['policy_no'],
                              vehicle_id=vehicle_id)
    db.session.add(new_insurance)
    db.session.commit()
    return jsonify({'message': 'Insurance record registered successfully'}), 201


  # get all maintenance records for vehicle
  @app.route('/vehicle/<int:vehicle_id>/maintenance', methods=['GET'])
  def get_maintenance_records(vehicle_id):
    vehicle = db.session.query(Vehicle).get(vehicle_id)
    if not vehicle:
      return jsonify({'error': 'Vehicle not found'}), 404

    maintenance_records = db.session.query(MaintenanceRecord).filter_by(vehicle_id=vehicle_id).all()
    if not maintenance_records:
      return jsonify({'message': 'No maintenance records found for this vehicle'}), 200

    maintenance_list = []
    for record in maintenance_records:
      maintenance_info = {
        'maintenance_id': record.maintenance_id,
        'wiper_fluid_refilled': record.wiper_fluid_refilled,
        'wipers_changed': record.wipers_changed,
        'oil_changed': record.oil_changed,
        'service_date': record.service_date.strftime('%Y-%m-%d'),  # Format date as string
        'battery_status': record.battery_status,
        'air_filter_changed': record.air_filter_changed,
        'tires_changed': record.tires_changed,
        'tires_rotated': record.tires_rotated,
        'brakes_replaced': record.brakes_replaced,
        'vehicle_id': record.vehicle_id
      }
      maintenance_list.append(maintenance_info)

    return jsonify(maintenance_list), 200

  # add a maintenance record for a vehicle
  @app.route('/vehicle/<int:vehicle_id>/maintenance', methods=['POST'])
  def add_maintenance_record(vehicle_id):
    maintenance_data = request.get_json()
    vehicle = db.session.query(Vehicle).get(vehicle_id)
    if not vehicle:
      return jsonify({'error': 'Vehicle not found'}), 404

    new_maintenance = MaintenanceRecord(vehicle_id=vehicle_id, **maintenance_data)
    db.session.add(new_maintenance)
    db.session.commit()
    return jsonify({'message': 'Maintenance record added successfully'}), 201

if __name__ == '__main__':
  app.run(debug=True)
  
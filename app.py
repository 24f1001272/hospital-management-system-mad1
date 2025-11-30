from flask import Flask
from common import db, login_manager
from models import User, Department
from routes import home, auth, admin, doctor, patient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hms.sqlite3'
    app.config['SECRET_KEY'] = 'hms_secret_key'

    app.template_folder = 'templates'

    db.init_app(app)

    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        if isinstance(dbapi_conn, SQLite3Connection):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    with app.app_context():
        db.create_all()
        if not Department.query.first():
            departments = [
                Department(name='Neurology', description='The Neurology Department specializes in the diagnosis and treatment of disorders of the nervous system, including the brain, spinal cord, nerves, and muscles. Our team of experts handles conditions such as stroke, epilepsy, multiple sclerosis, and Parkinson\'s disease.'),
                Department(name='Cardiology', description='The Cardiology Department provides comprehensive care for heart and vascular conditions. From preventative screenings to advanced surgical interventions, our cardiologists are dedicated to maintaining your heart health.'),
                Department(name='Gastroenterology', description='The Gastroenterology Department focuses on the digestive system and its disorders. We offer advanced diagnostic and therapeutic procedures for conditions affecting the esophagus, stomach, intestines, liver, and pancreas.'),
                Department(name='Oncology', description='The Oncology Department is dedicated to the diagnosis, treatment, and care of patients with cancer. It houses a team of specialized doctors, such as medical oncologists, surgical oncologists, and radiation oncologists, who work together to provide comprehensive cancer care.'),
            ]
            db.session.bulk_save_objects(departments)
            db.session.commit()
            
        if not User.query.filter_by(role='admin').first():
            admin_ = User(username='admin', email='admin@hospital.com', role='admin', name='Hospital Admin')
            admin_.set_password('adminpass')
            db.session.add(admin_)
            db.session.commit()

    login_manager.init_app(app)

    app.register_blueprint(home.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(doctor.bp)
    app.register_blueprint(patient.bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

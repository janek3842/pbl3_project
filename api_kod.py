from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_restx import Api, Resource, fields
import os, base64
from datetime import datetime, timedelta
from obj_rec import objRec
from ultralytics import YOLO

# Konfiguracja czasu dla strefy czasowej UTC+1
utcplusone = lambda: datetime.utcnow() + timedelta(hours=1)
# Wybranie modelu do analizy zdjęć
yolo = YOLO("yolov8n.pt")
# Konfiguracja aplikacji Flask
app = Flask(__name__)
api = Api(app, version='1.0', title='Sensor Management API', description='API do zarządzania danymi z czujników')

# Konfiguracja bazy danych
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# Modele danych
class SensorDevice(db.Model):
    #    id = db.Column(db.Integer, nullable=False)
    device_id = db.Column(db.String(50), primary_key=True)  # Ustawienie jako klucz główny
    room_id = db.Column(db.String(50), nullable=False)
    device_type = db.Column(db.String(50), default='sensor')  # Typ urządzenia: sensor
    added_on = db.Column(db.DateTime, default=utcplusone)

    # Relacja z SensorData
    sensor_data = db.relationship(
        'SensorData',  # Nazwa tabeli docelowej (modelu)
        back_populates='sensor_device',  # Powiązanie zwrotne
        cascade="all, delete-orphan"  # Usuwanie powiązanych rekordów
    )


class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), nullable=False)
    device_id = db.Column(db.String(50), db.ForeignKey('sensor_device.device_id'))  # Klucz obcy
    temperature = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    smoke_level = db.Column(db.Integer, nullable=True)
    timestamp = db.Column(db.DateTime, default=utcplusone)

    # Relacja z SensorDevice
    sensor_device = db.relationship('SensorDevice', back_populates='sensor_data')

    def __repr__(self):
        return f'<SensorData {self.device_id} at {self.timestamp}>'


class CameraDevice(db.Model):
    device_id = db.Column(db.String(50), primary_key=True)
    room_id = db.Column(db.String(50), nullable=False)
    device_type = db.Column(db.String(50), default='camera')  # Typ urządzenia: camera
    added_on = db.Column(db.DateTime, default=utcplusone)
    # Relacja z Image
    image = db.relationship(
        'Image',  # Nazwa tabeli docelowej (modelu)
        back_populates='camera_device',  # Powiązanie zwrotne
        cascade="all, delete-orphan"  # Usuwanie powiązanych rekordów
    )


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), db.ForeignKey('camera_device.device_id'))
    section = db.Column(db.String(1), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    timestamp = db.Column(db.DateTime, default=utcplusone)
    # Relacja z SensorDevice
    camera_device = db.relationship('CameraDevice', back_populates='image')


class ImageOut(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(1), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)
    timestamp = db.Column(db.DateTime, default=utcplusone)
    people_num = db.Column(db.Integer, nullable=False)


# Tworzenie tabel w bazie danych jeśli nie istnieją
with app.app_context():
    db.create_all()

# Namespace i modele dla RESTx
ns = api.namespace('rooms', description='Zarządzanie urządzeniami i danymi w pokojach')

device_model = api.model('Device', {
    'device_id': fields.String(required=True, description='ID urządzenia')
})

data_model = api.model('SensorData', {
    'temperature': fields.Float(description='Temperatura'),
    'humidity': fields.Float(description='Wilgotność'),
    'smoke_level': fields.Integer(description='Poziom zadymienia')
})


@ns.route('/<string:room_id>/sensor-devices')
class SensorDeviceResource(Resource):
    @api.expect(device_model)
    def post(self, room_id):
        """Dodaj nowe urządzenie czujnikowe do pokoju"""
        data = request.get_json()
        device_id = data.get('device_id')

        # Sprawdź, czy urządzenie już istnieje
        if SensorDevice.query.filter_by(device_id=device_id).first():
            return {"error": "Urządzenie czujnikowe już istnieje"}, 400

        new_sensor_device = SensorDevice(device_id=device_id, room_id=room_id)
        db.session.add(new_sensor_device)
        db.session.commit()

        return {"message": "Urządzenie czujnikowe dodane pomyślnie"}, 201

    def get(self, room_id):
        """Pobierz listę urządzeń czujnikowych w pokoju"""
        sensor_devices = SensorDevice.query.filter_by(room_id=room_id).all()

        if not sensor_devices:
            return {"error": "Brak urządzeń czujnikowych w tym pokoju"}, 404

        result = [
            {
                "device_id": device.device_id,
                "device_type": device.device_type,
                "added_on": device.added_on.isoformat()
            }
            for device in sensor_devices
        ]

        return {"sensor_devices": result}, 200


@ns.route('/<string:room_id>/cameras')
class CameraDeviceResource(Resource):
    @api.expect(device_model)
    def post(self, room_id):
        """Dodaj nowe urządzenie kamery do pokoju"""
        data = request.get_json()
        device_id = data.get('device_id')

        # Sprawdź, czy urządzenie już istnieje
        if CameraDevice.query.filter_by(device_id=device_id).first():
            return {"error": "Urządzenie kamery już istnieje"}, 400

        new_camera_device = CameraDevice(device_id=device_id, room_id=room_id)
        db.session.add(new_camera_device)
        db.session.commit()

        return {"message": "Urządzenie kamery dodane pomyślnie"}, 201


@ns.route('/<string:room_id>/sensor-devices/<string:device_id>')
class DeleteSensorDeviceResource(Resource):
    def delete(self, room_id, device_id):
        """Usuń urządzenie czujnikowe"""
        # Wyszukaj urządzenie w bazie danych
        sensor_device = SensorDevice.query.filter_by(room_id=room_id, device_id=device_id).first()

        if not sensor_device:
            return {"error": "Urządzenie czujnikowe nie istnieje"}, 404

        # Usuń urządzenie
        db.session.delete(sensor_device)
        db.session.commit()

        return {"message": "Urządzenie czujnikowe zostało usunięte"}, 200


@ns.route('/<string:room_id>/cameras/<string:device_id>')
class DeleteCameraDeviceResource(Resource):
    def delete(self, room_id, device_id):
        """Usuń urządzenie kamery"""
        # Wyszukaj urządzenie w bazie danych
        camera_device = CameraDevice.query.filter_by(room_id=room_id, device_id=device_id).first()

        if not camera_device:
            return {"error": "Urządzenie kamery nie istnieje"}, 404

        # Usuń urządzenie
        db.session.delete(camera_device)
        db.session.commit()

        return {"message": "Urządzenie kamery zostało usunięte"}, 200


@ns.route('/<string:room_id>/sensor-devices/<string:device_id>/limits')
class SensorLimitsResource(Resource):
    @api.expect(data_model)
    def put(self, room_id, device_id):
        data = request.get_json()
        if not data:
            return {"error": "Brak danych do zapisania"}, 400

        self.temp_limit = data.get('temperature')
        self.hum_limit = data.get('humidity')
        self.smoke_limit = data.get('smoke_level')
        self.ppl_limit = data.get('people')

        return {"message": "Dane zaktualizowane pomyślnie"}, 200

    def get(self, room_id, device_id):
        limits = {
            "temp limit": self.temp_limit,
            "hum_limit": self.hum_limit,
            "smoke_limit": self.smoke_limit,
            "ppl_limit": self.ppl_limit
        }

        return limits, {200}


@ns.route('/<string:room_id>/sensor-devices/<string:device_id>/data')
class SensorDataResource(Resource):
    @api.expect(data_model)
    def put(self, room_id, device_id):
        """Aktualizuj dane z czujnika"""

        data = request.get_json()
        if not data:
            return {"error": "Brak danych do zapisania"}, 400

        temperature = data.get('temperature')
        humidity = data.get('humidity')
        smoke_level = data.get('smoke_level')

        # Utwórz nowy rekord z danymi
        new_record = SensorData(
            room_id=room_id,
            device_id=device_id,
            temperature=temperature,
            humidity=humidity,
            smoke_level=smoke_level
        )
        db.session.add(new_record)
        db.session.commit()

        return {"message": "Dane zaktualizowane pomyślnie"}, 200

    def get(self, room_id, device_id):
        """Pobierz najnowsze dane z czujnika na podstawie id"""
        # Pobierz rekord o najwyższym id dla podanego room_id i device_id
        latest_data = (
            SensorData.query.filter_by(room_id=room_id, device_id=device_id)
            .order_by(SensorData.id.desc())  # Sortowanie malejące po id
            .first()  # Pobierz pierwszy rekord
        )

        if not latest_data:
            return {"error": "Nie znaleziono danych dla urządzenia"}, 404

        # Przygotowanie wyniku w formacie JSON
        result = {
            "id": latest_data.id,
            "temperature": latest_data.temperature,
            "humidity": latest_data.humidity,
            "smoke_level": latest_data.smoke_level,
            "timestamp": latest_data.timestamp.isoformat()  # Konwersja na ISO 8601
        }

        return {"data": result}, 200


@ns.route('/<string:room_id>/sensor-devices/<string:device_id>/data/<string:metric_type>')
class MetricDataResource(Resource):
    def get(self, room_id, device_id, metric_type):
        """Pobierz dane dla konkretnego typu pomiaru"""
        if metric_type not in ["temperature", "humidity", "smoke_level"]:
            return {"error": "Nieprawidłowy typ pomiaru, oczekiwano: temperature, humidity lub smoke_level"}, 400

        data = SensorData.query.filter_by(room_id=room_id, device_id=device_id).all()
        if not data:
            return {"error": "Nie znaleziono danych dla urządzenia"}, 404

        result = [
            {"id": record.id, metric_type: getattr(record, metric_type), "timestamp": record.timestamp}
            for record in data if getattr(record, metric_type) is not None
        ]

        return {"data": result}, 200


@ns.route('/<string:room_id>/cameras/<string:device_id>/images')
class ImageUploadResource(Resource):
    def post(self, room_id, device_id):
        """Prześlij zdjęcie do urządzenia"""
        if 'file' not in request.files:
            return {"error": "Brak pliku w żądaniu"}, 400

        file = request.files['file']
        if file.filename == '':
            return {"error": "Nie wybrano pliku"}, 400

        # Sprawdzenie formatu pliku
        if not file.filename.lower().endswith(('.jpg', '.jpeg')):
            return {"error": "Nieprawidłowy format pliku, dozwolone są tylko pliki JPG"}, 400

        # Odczytanie danych obrazu
        image_data = file.read()
        temp_file_path = 'static/temp_image.jpg'
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(image_data)

        # Sprawdzenie liczby osób
        file_path_out = 'static/image_out/'
        people_num, file_path_out_fin = objRec(temp_file_path, file_path_out, yolo)

        with open(file_path_out_fin, 'rb') as analyzed_file:
            analyzed_image_data = analyzed_file.read()

        # Zapisanie zdjęć do bazy danych
        image = Image(image_data=image_data, section=room_id)
        db.session.add(image)

        image_out = ImageOut(image_data=analyzed_image_data, people_num=people_num, section=room_id)
        db.session.add(image_out)

        db.session.commit()

        # Usunięcie tymczasowych plików
        os.remove(temp_file_path)
        os.remove(file_path_out_fin)

        return {"message": "Zdjęcie przesłane i przetworzone pomyślnie", "people_num": people_num}, 200

    def get(self, room_id, device_id):
        """Pobierz najnowsze zdjęcia dla urządzenia"""
        original_image = Image.query.filter_by(section=room_id).order_by(Image.id.desc()).first()
        processed_image = ImageOut.query.filter_by(section=room_id).order_by(ImageOut.id.desc()).first()

        if not original_image or not processed_image:
            return {"error": "Brak zdjęć dla tego urządzenia"}, 404

        result = {
            "original_image": base64.b64encode(original_image.image_data).decode('utf-8'),
            "processed_image": base64.b64encode(processed_image.image_data).decode('utf-8'),
            "people_num": processed_image.people_num,
            "timestamp": processed_image.timestamp
        }

        return {"data": result}, 200


@app.route('/site')
def home():
    """Funkcja wyświetlająca dane na stronie HTML"""
    # Pobranie najnowszych danych z czujników dla każdej sekcji
    sensor_data = {
        'A': SensorData.query.filter_by(room_id='A').order_by(SensorData.id.desc()).first(),
        'B': SensorData.query.filter_by(room_id='B').order_by(SensorData.id.desc()).first(),
        'C': SensorData.query.filter_by(room_id='C').order_by(SensorData.id.desc()).first()
    }

    # Pobranie najnowszych zdjęć oryginalnych i przetworzonych dla każdej sekcji
    images_base64 = {}
    for section in ['A', 'B', 'C']:
        original_image = Image.query.filter_by(section=section).order_by(Image.id.desc()).first()
        processed_image = ImageOut.query.filter_by(section=section).order_by(ImageOut.id.desc()).first()

        images_base64[section] = {
            "original": base64.b64encode(original_image.image_data).decode('utf-8') if original_image else None,
            "processed": base64.b64encode(processed_image.image_data).decode('utf-8') if processed_image else None,
            "people_num": processed_image.people_num if processed_image else None,
            "timestamp": processed_image.timestamp if processed_image else None
        }

    # Przekazanie danych do szablonu HTML
    return render_template(
        'index.html',
        sensor_data=sensor_data,
        images_base64=images_base64
    )


if __name__ == '__main__':
    # Obsługa ustawienia REST API
    api.add_namespace(ns, path='/rooms')

    # Uruchomienie serwera Flask
    app.run(
        host='0.0.0.0',  # Hostuj na wszystkich dostępnych interfejsach
        port=1880,  # Port serwera
        debug=True  # Debugowanie (można wyłączyć w środowisku produkcyjnym)
    )
from flask import Flask, render_template, request, redirect, session, jsonify
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import urllib.parse

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "parking_secret_key")

# =========================
# UPLOAD FOLDER
# =========================

UPLOAD_FOLDER = "static/uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =========================
# DATABASE CONFIGURATION
# =========================

def get_db_config():
    """Mengambil konfigurasi database dari environment variables."""

    database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

    if database_url:
        parsed = urllib.parse.urlparse(database_url)
        return {
            'host': parsed.hostname,
            'user': parsed.username,
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/'),
            'port': parsed.port or 3306,
            'cursorclass': pymysql.cursors.DictCursor
        }

    return {
        'host': os.getenv("MYSQLHOST", os.getenv("MYSQL_HOST", "localhost")),
        'user': os.getenv("MYSQLUSER", os.getenv("MYSQL_USER", "root")),
        'password': os.getenv("MYSQLPASSWORD", os.getenv("MYSQL_PASSWORD", "")),
        'database': os.getenv("MYSQLDATABASE", os.getenv("MYSQL_DB", "")),
        'port': int(os.getenv("MYSQLPORT", os.getenv("MYSQL_PORT", "3306"))),
        'cursorclass': pymysql.cursors.DictCursor
    }

def get_db_connection():
    """Membuat koneksi database baru."""
    config = get_db_config()
    return pymysql.connect(**config)

# =========================
# AUTO CREATE TABLES
# =========================

def init_db():
    """Membuat tabel jika belum ada."""
    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Tabel users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama VARCHAR(100) NOT NULL,
                nim VARCHAR(20) NOT NULL,
                fakultas VARCHAR(100) NOT NULL,
                nohp VARCHAR(20) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) DEFAULT 'user'
            )
        """)

        # Tabel area_parkir
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS area_parkir (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama_area VARCHAR(100) NOT NULL,
                kapasitas INT DEFAULT 0,
                terisi INT DEFAULT 0,
                latitude DECIMAL(10, 8) DEFAULT NULL,
                longitude DECIMAL(11, 8) DEFAULT NULL,
                deskripsi TEXT
            )
        """)

        # Tabel laporan
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laporan (
                id INT AUTO_INCREMENT PRIMARY KEY,
                area VARCHAR(100) NOT NULL,
                plat VARCHAR(20) NOT NULL,
                keterangan TEXT,
                foto VARCHAR(255),
                status VARCHAR(50) DEFAULT 'Belum Dibaca',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabel logs_parkir (untuk riwayat parkir)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_parkir (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama_user VARCHAR(100) NOT NULL,
                nim VARCHAR(20) NOT NULL,
                area VARCHAR(100) NOT NULL,
                plat VARCHAR(20) NOT NULL,
                waktu_masuk DATETIME DEFAULT CURRENT_TIMESTAMP,
                waktu_keluar DATETIME DEFAULT NULL,
                status VARCHAR(50) DEFAULT 'Parkir'
            )
        """)

        db.commit()
        cursor.close()
        db.close()
        print("[INFO] Database initialized successfully")

    except Exception as e:
        print(f"[ERROR] Database init failed: {e}")

# =========================
# AUTO CREATE ADMIN
# =========================

def create_admin():
    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email=%s", ("admin@gmail.com",))
        admin = cursor.fetchone()

        if not admin:
            password_hash = generate_password_hash("admin123")
            cursor.execute("""
                INSERT INTO users (nama, nim, fakultas, nohp, email, password, role)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                "Administrator", "000000", "Admin",
                "08123456789", "admin@gmail.com", password_hash, "admin"
            ))
            db.commit()

        cursor.close()
        db.close()

    except Exception as e:
        print(f"[WARNING] Gagal membuat admin: {e}")

# =========================
# INISIALISASI SAAT MODULE LOAD
# =========================

_db_initialized = False

if not _db_initialized:
    init_db()
    create_admin()
    _db_initialized = True

# =========================
# ROUTES
# =========================

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/do_register', methods=['POST'])
def do_register():
    try:
        nama = request.form['nama']
        nim = request.form['nim']
        fakultas = request.form['fakultas']
        nohp = request.form['nohp']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        cek = cursor.fetchone()

        if cek:
            cursor.close()
            db.close()
            return "Email sudah terdaftar!"

        cursor.execute("""
            INSERT INTO users (nama, nim, fakultas, nohp, email, password, role)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (nama, nim, fakultas, nohp, email, password, "user"))

        db.commit()
        cursor.close()
        db.close()

        return redirect('/')

    except Exception as e:
        return f"Error saat registrasi: {str(e)}", 500

@app.route('/login', methods=['POST'])
def do_login():
    try:
        email = request.form['email']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['login'] = True
            session['nama'] = user['nama']
            session['role'] = user['role']
            session['email'] = user['email']
            return redirect('/dashboard')

        return "Login gagal!"

    except Exception as e:
        return f"Error saat login: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    if 'login' not in session:
        return redirect('/')
    if session['role'] == 'admin':
        return render_template('dashboard_admin.html')
    return render_template('dashboard_user.html')

@app.route('/lihat_area')
def lihat_area():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM area_parkir")
        data = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('lihat_area.html', area=data)
    except Exception as e:
        return f"Error: {str(e)}", 500

# =========================
# PETA PARKIR
# =========================

@app.route('/peta')
def peta_redirect():
    if 'login' not in session:
        return redirect('/')
    
    return render_template('peta.html')

# =========================
# LOGS PARKIR
# =========================

@app.route('/logs_parkir')
def logs_parkir():
    if 'login' not in session:
        return redirect('/')

    try:
        db = get_db_connection()
        cursor = db.cursor()

        # Jika admin, lihat semua logs. Jika user, lihat logs miliknya sendiri
        if session.get('role') == 'admin':
            cursor.execute("SELECT * FROM logs_parkir ORDER BY waktu_masuk DESC")
        else:
            cursor.execute(
                "SELECT * FROM logs_parkir WHERE nim=%s ORDER BY waktu_masuk DESC",
                (session.get('nim', ''),)
            )

        data = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('logs_parkir.html', logs=data)
    except Exception as e:
        return f"Error: {str(e)}", 500

# =========================
# PROFIL
# =========================

@app.route('/profil')
def profil():
    if 'login' not in session:
        return redirect('/')
    return render_template('profil.html')

# =========================
# LAPOR PARKIR LIAR
# =========================

@app.route('/lapor_parkir_liar', methods=['GET', 'POST'])
def lapor_parkir_liar():
    if 'login' not in session:
        return redirect('/')

    if request.method == 'POST':
        try:
            area = request.form['area']
            plat = request.form['plat']
            keterangan = request.form['keterangan']
            foto = request.files['foto']
            filename = secure_filename(foto.filename)

            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            db = get_db_connection()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO laporan (area, plat, keterangan, foto, status)
                VALUES (%s,%s,%s,%s,%s)
            """, (area, plat, keterangan, filename, "Belum Dibaca"))

            db.commit()
            cursor.close()
            db.close()

            return redirect('/dashboard')

        except Exception as e:
            return f"Error saat melapor: {str(e)}", 500

    return render_template('lapor_parkir_liar.html')

# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# =========================
# RUN APP (untuk local development)
# =========================

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

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

    # Cek apakah Railway menyediakan DATABASE_URL atau MYSQL_URL
    database_url = os.getenv("DATABASE_URL") or os.getenv("MYSQL_URL")

    if database_url:
        # Parse dari URL (format: mysql://user:pass@host:port/dbname)
        parsed = urllib.parse.urlparse(database_url)
        return {
            'host': parsed.hostname,
            'user': parsed.username,
            'password': parsed.password or '',
            'database': parsed.path.lstrip('/'),
            'port': parsed.port or 3306,
            'cursorclass': pymysql.cursors.DictCursor
        }

    # Fallback ke individual variables dengan default values
    return {
        'host': os.getenv("MYSQLHOST", os.getenv("MYSQL_HOST", "localhost")),
        'user': os.getenv("MYSQLUSER", os.getenv("MYSQL_USER", "root")),
        'password': os.getenv("MYSQLPASSWORD", os.getenv("MYSQL_PASSWORD", "")),
        'database': os.getenv("MYSQLDATABASE", os.getenv("MYSQL_DB", "")),
        'port': int(os.getenv("MYSQLPORT", os.getenv("MYSQL_PORT", "3306"))),
        'cursorclass': pymysql.cursors.DictCursor
    }

def get_db_connection():
    """Membuat koneksi database baru setiap kali dipanggil."""
    config = get_db_config()
    return pymysql.connect(**config)

# =========================
# AUTO CREATE ADMIN
# =========================

def create_admin():
    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            ("admin@gmail.com",)
        )

        admin = cursor.fetchone()

        if not admin:
            password_hash = generate_password_hash("admin123")

            cursor.execute("""
                INSERT INTO users
                (nama, nim, fakultas, nohp, email, password, role)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                "Administrator",
                "000000",
                "Admin",
                "08123456789",
                "admin@gmail.com",
                password_hash,
                "admin"
            ))

            db.commit()

        cursor.close()
        db.close()

    except Exception as e:
        print(f"[WARNING] Gagal membuat admin: {e}")

# =========================
# LOGIN PAGE
# =========================

@app.route('/')
def login():
    return render_template('login.html')

# =========================
# REGISTER PAGE
# =========================

@app.route('/register')
def register():
    return render_template('register.html')

# =========================
# REGISTER PROCESS
# =========================

@app.route('/do_register', methods=['POST'])
def do_register():
    nama = request.form['nama']
    nim = request.form['nim']
    fakultas = request.form['fakultas']
    nohp = request.form['nohp']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    cek = cursor.fetchone()

    if cek:
        cursor.close()
        db.close()
        return "Email sudah terdaftar!"

    cursor.execute("""
        INSERT INTO users
        (nama, nim, fakultas, nohp, email, password, role)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (
        nama,
        nim,
        fakultas,
        nohp,
        email,
        password,
        "user"
    ))

    db.commit()
    cursor.close()
    db.close()

    return redirect('/')

# =========================
# LOGIN PROCESS
# =========================

@app.route('/login', methods=['POST'])
def do_login():
    email = request.form['email']
    password = request.form['password']

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

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

# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
def dashboard():
    if 'login' not in session:
        return redirect('/')

    if session['role'] == 'admin':
        return render_template('dashboard_admin.html')

    return render_template('dashboard_user.html')

# =========================
# AREA PARKIR
# =========================

@app.route('/lihat_area')
def lihat_area():
    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM area_parkir")
    data = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('lihat_area.html', area=data)

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
        area = request.form['area']
        plat = request.form['plat']
        keterangan = request.form['keterangan']

        foto = request.files['foto']
        filename = secure_filename(foto.filename)

        foto.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename
            )
        )

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO laporan
            (area, plat, keterangan, foto, status)
            VALUES (%s,%s,%s,%s,%s)
        """, (
            area,
            plat,
            keterangan,
            filename,
            "Belum Dibaca"
        ))

        db.commit()
        cursor.close()
        db.close()

        return redirect('/dashboard')

    return render_template('lapor_parkir_liar.html')

# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# =========================
# RUN APP
# =========================

if __name__ == '__main__':
    # Buat admin saat pertama kali run (opsional)
    create_admin()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

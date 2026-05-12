from flask import Flask, render_template, request, redirect, session, jsonify
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "parking_secret_key"

# =========================
# UPLOAD FOLDER
# =========================

UPLOAD_FOLDER = "static/uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =========================
# DATABASE RAILWAY
# =========================

db = pymysql.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT")),
    cursorclass=pymysql.cursors.DictCursor
)

# =========================
# AUTO CREATE ADMIN
# =========================

def create_admin():
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

create_admin()

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

    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    cek = cursor.fetchone()

    if cek:
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

    return redirect('/')

# =========================
# LOGIN PROCESS
# =========================

@app.route('/login', methods=['POST'])
def do_login():

    email = request.form['email']
    password = request.form['password']

    cursor = db.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (email,)
    )

    user = cursor.fetchone()

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

    cursor = db.cursor()

    cursor.execute("SELECT * FROM area_parkir")

    data = cursor.fetchall()

    return render_template(
        'lihat_area.html',
        area=data
    )

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

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host='0.0.0.0',
        port=port
    )
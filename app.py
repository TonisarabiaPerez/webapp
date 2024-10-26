from flask import Flask, render_template, request, redirect, url_for, session  # type: ignore
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin  # type: ignore
import sqlite3

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'  # Para gestionar las sesiones

login_manager = LoginManager()
login_manager.init_app(app)

# Conectar a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('periciales.db')
    conn.row_factory = sqlite3.Row  # Esto devuelve las filas como diccionarios
    return conn

# Clase de usuario para manejar login en Flask
class Usuario(UserMixin):
    def __init__(self, id, nombre, username, rol):
        self.id = id
        self.nombre = nombre
        self.username = username
        self.rol = rol

# Cargar usuario por ID
@login_manager.user_loader
def cargar_usuario(id):
    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (id,)).fetchone()
    conn.close()
    if usuario is None:
        return None
    return Usuario(usuario['id'], usuario['nombre'], usuario['username'], usuario['rol'])

# Ruta para iniciar sesión
@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if usuario:
            user = Usuario(usuario['id'], usuario['nombre'], usuario['username'], usuario['rol'])
            login_user(user)
            session['username'] = user.username  # Añadir a la sesión
            return redirect(url_for('index'))
        else:
            return "Credenciales incorrectas"
    
    return render_template('login.html')

# Ruta para cerrar sesión
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Crear la tabla de informes si no existe
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS informes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            fecha DATE NOT NULL
        )
    ''')
    # Crear tabla de usuarios
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('administrador', 'perito', 'supervisor'))
        )
    ''')
    
    # Insertar un administrador inicial solo si no existe
    conn.execute('''
        INSERT OR IGNORE INTO usuarios (nombre, username, password, rol)
        VALUES ('Admin', 'admin', 'adminpass', 'administrador')
    ''')
    
    conn.commit()
    conn.close()

# Ruta principal (solo usuarios logueados)
@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    informes = conn.execute('SELECT * FROM informes').fetchall()
    conn.close()
    return render_template('index.html', informes=informes)

# Ruta para crear informes (solo peritos o administradores)
@app.route('/crear', methods=('GET', 'POST'))
@login_required
def crear():
    if current_user.rol not in ['administrador', 'perito']:
        return "No tienes permiso para crear informes"
    
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha = request.form['fecha']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO informes (titulo, descripcion, fecha) VALUES (?, ?, ?)',
                     (titulo, descripcion, fecha))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('crear.html')

# Inicializar la base de datos
if __name__ == '__main__':
    init_db()
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from backend.sistema import SistemaBackend # Importamos tu backend existente

app = Flask(__name__)
app.secret_key = "mi_clave_super_secreta" # Necesario para guardar la sesión del usuario

# Instanciamos tu base de datos
db = SistemaBackend()

# --- RUTA 1: LOGIN (Página de inicio) ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Recogemos los datos del formulario HTML
        usuario = request.form['username']
        password = request.form['password']
        
        # Usamos TU lógica de backend
        exito, rol = db.autenticar(usuario, password)
        
        if exito:
            # Guardamos datos en la "sesión" (memoria del navegador)
            session['usuario'] = usuario
            session['rol'] = rol
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos")
            
    return render_template('login.html')

# --- RUTA DE REGISTRO (Actualizada) ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # 1. Recoger datos básicos
        rol = request.form['rol'] # 'cliente' o 'consultor'
        nombre = request.form['nombre']
        email = request.form['email']
        usuario = request.form['username']
        password = request.form['password']
        
        # 2. Recoger datos extra (solo si es consultor)
        especialidad = "General"
        tarifa = 0
        
        if rol == 'consultor':
            especialidad = request.form.get('especialidad', 'General')
            try:
                tarifa = float(request.form.get('tarifa', 0))
            except ValueError:
                tarifa = 0
        
        # 3. Guardar en Base de Datos usando tu backend
        exito, msg = db.registrar_usuario(
            usuario, password, nombre, email, 
            rol=rol, 
            especialidad=especialidad, 
            tarifa=tarifa
        )
        
        if exito:
            flash(f"¡Registro como {rol} exitoso! Inicia sesión.")
            return redirect(url_for('login'))
        else:
            flash(f"Error: {msg}")
            
    return render_template('register.html')

# --- RUTA 2: DASHBOARD (Actualizada) ---
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    rol = session['rol']
    
    # 1. Recuperamos la lista de consultores para el menú desplegable
    consultores = db.get_consultores_disponibles()
    
    # 2. Recuperamos las reservas existentes para la tabla
    if rol == 'cliente':
        reservas = db.get_reservas_cliente(usuario)
    else:
        reservas = db.get_reservas_consultor(usuario)
    
    # Enviamos todo al HTML
    return render_template('dashboard.html', usuario=usuario, rol=rol, consultores=consultores, reservas=reservas)

# --- RUTA NUEVA: PROCESAR LA CITA ---
@app.route('/crear_cita', methods=['POST'])
def crear_cita():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    # Recogemos los datos del formulario HTML
    consultor_nombre = request.form['consultor']
    fecha_html = request.form['fecha'] # Viene como "2023-12-12T14:30"
    
    # Pequeño truco: Python espera espacio en vez de 'T' entre fecha y hora
    fecha_final = fecha_html.replace('T', ' ')
    
    exito, msg = db.crear_reserva(usuario, consultor_nombre, fecha_final)
    
    if exito:
        flash("¡Cita agendada con éxito!")
    else:
        flash(f"Error: {msg}")
        
    return redirect(url_for('dashboard'))

# --- RUTA 3: CERRAR SESIÓN ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
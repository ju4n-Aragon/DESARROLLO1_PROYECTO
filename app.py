from flask import Flask, render_template, request, redirect, url_for, flash, session
from backend.sistema import SistemaBackend
from datetime import datetime  # Para manejar fechas
app = Flask(__name__)
app.secret_key = "secreto_seguro"  # Necesario para usar flash messages y session

# Conectamos con el backend del sistema 
db = SistemaBackend()

# --- RUTA 1: LOGIN --
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        password = request.form['password']
        
        exito, user_id = db.autenticar(usuario, password)
        
        if exito:
            # Guardamos datos en la sesión del navegador
            session['usuario'] = usuario
            datos_usuario = db.get_usuario(usuario)
            session['rol'] = datos_usuario['rol']
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos")
            
    return render_template('login.html')

# --- RUTA 2: REGISTRO ---
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        rol = request.form['rol']
        nombre = request.form['nombre']
        email = request.form['email']
        usuario = request.form['username']
        password = request.form['password']
        
        # Valores por defecto
        especialidad = "General"
        tarifa = 0
        descripcion = ""
        experiencia_años = 0
        primera_cita_descuento = False
        porcentaje_descuento = 0
        
        if rol == 'consultor':
            especialidad = request.form.get('especialidad', 'General')
            try:
                tarifa = float(request.form.get('tarifa', 0))
            except ValueError:
                tarifa = 0
            
            # Nuevos campos
            descripcion = request.form.get('descripcion', '')
            experiencia_años = int(request.form.get('experiencia_años', 0))
            
            # Checkbox devuelve 'true' si está marcado
            primera_cita_descuento = request.form.get('primera_cita_descuento') == 'true'
            
            if primera_cita_descuento:
                try:
                    porcentaje_descuento = float(request.form.get('porcentaje_descuento', 0))
                except ValueError:
                    porcentaje_descuento = 0
        
        exito, msg = db.registrar_usuario(
            usuario, password, nombre, email, 
            rol=rol, 
            especialidad=especialidad, 
            tarifa=tarifa,
            descripcion=descripcion,
            experiencia_años=experiencia_años,
            primera_cita_descuento=primera_cita_descuento,
            porcentaje_descuento=porcentaje_descuento
        )
        
        if exito:
            flash(f"¡Registro como {rol} exitoso! Inicia sesión.")
            return redirect(url_for('login'))
        else:
            flash(f"Error: {msg}")
            
    return render_template('register.html')
# --- RUTA 3: DASHBOARD (PANEL PRINCIPAL) ---
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: 
        return redirect(url_for('login'))
    
    usuario = session['usuario']
    rol = session['rol']
    
    consultores = db.get_consultores_disponibles()
    ganancias = 0
    
    if rol == 'cliente':
        reservas = db.get_reservas_cliente(usuario)
    else:
        reservas = db.get_reservas_consultor(usuario)
        ganancias = db.calcular_ganancias_consultor(usuario)
    
    # Pasar la fecha actual al template
    return render_template('dashboard.html', 
                         usuario=usuario, 
                         rol=rol, 
                         consultores=consultores, 
                         reservas=reservas, 
                         ganancias=ganancias,
                         now=datetime.now())
# --- RUTA 4: CREAR CITA ---
@app.route('/crear_cita', methods=['POST'])
def crear_cita():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    consultor_nombre = request.form['consultor']
    fecha_html = request.form['fecha']
    
    exito, msg = db.crear_reserva(usuario, consultor_nombre, fecha_html)
    
    if exito:
        flash("¡Cita agendada con éxito!")
    else:
        flash(f"Error: {msg}")
        
    return redirect(url_for('dashboard'))

# --- RUTA 5: GESTIONAR CITA (NUEVA) ---
# Esta ruta recibe los clics de "Completar" o "Cancelar"
@app.route('/gestionar_cita', methods=['POST'])
def gestionar_cita():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    id_reserva = request.form['id_reserva']
    accion = request.form['accion'] # 'completar' o 'cancelar'
    notas = request.form.get('notas', '') 
    
    if accion == 'completar':
        db.actualizar_estado_cita(id_reserva, 'Completada', notas)
        flash("¡Cita completada! Honorarios sumados.")
    elif accion == 'cancelar':
        db.actualizar_estado_cita(id_reserva, 'Cancelada', "Cancelada por consultor.")
        flash("Cita cancelada.")
        
    return redirect(url_for('dashboard'))

# --- RUTA 6: CERRAR SESIÓN ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
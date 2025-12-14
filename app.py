from flask import Flask, render_template, request, redirect, url_for, flash, session
# IMPORTANTE: Si tu archivo se llama 'sistema.py' y está en la misma carpeta, usa:
from backend.sistema import SistemaBackend
# Si está dentro de una carpeta llamada 'backend', usa: from backend.sistema import SistemaBackend

from datetime import datetime

app = Flask(__name__)
app.secret_key = "secreto_seguro"

# Conectamos con el backend
db = SistemaBackend()

# --- RUTA 1: LOGIN ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        password = request.form['password']
        
        exito, user_id = db.autenticar(usuario, password)
        
        if exito:
            session['usuario'] = usuario
            datos_usuario = db.get_usuario(usuario)
            session['rol'] = datos_usuario['rol']
            # Guardamos el ID en sesión para usarlo luego si es necesario
            session['user_id'] = user_id 
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos")
            
    return render_template('login.html')

# --- RUTA 2: REGISTRO (CORREGIDA Y FINAL) ---
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
        experiencia_anos = 0 # Variable limpia (sin ñ) para Python
        primera_cita_descuento = False
        porcentaje_descuento = 0
        
        if rol == 'consultor':
            especialidad = request.form.get('especialidad', 'General')
            try:
                tarifa = float(request.form.get('tarifa', 0))
            except ValueError:
                tarifa = 0
            
            # --- CAPTURA DE DATOS EXTRA (Aporte de tu compañero) ---
            descripcion = request.form.get('descripcion', '')
            
            # CORRECCIÓN DEL ERROR: Leemos 'años' del HTML, guardamos en 'anos'
            try:
                experiencia_anos = int(request.form.get('experiencia_años', 0))
            except ValueError:
                experiencia_anos = 0
            
            # Checkbox HTML devuelve 'on' o 'true' si está marcado
            val_checkbox = request.form.get('primera_cita_descuento')
            primera_cita_descuento = (val_checkbox == 'true' or val_checkbox == 'on')
            
            if primera_cita_descuento:
                try:
                    porcentaje_descuento = float(request.form.get('porcentaje_descuento', 0))
                except ValueError:
                    porcentaje_descuento = 0
        
        # LLAMADA A LA BASE DE DATOS
        exito, msg = db.registrar_usuario(
            usuario, password, nombre_completo=nombre, email=email, 
            rol=rol, 
            especialidad=especialidad, 
            tarifa=tarifa,
            # Pasamos los argumentos corregidos (SIN Ñ):
            descripcion=descripcion,
            experiencia_anos=experiencia_anos, 
            primera_cita_descuento=primera_cita_descuento,
            porcentaje_descuento=porcentaje_descuento
        )
        
        if exito:
            flash(f"¡Registro como {rol} exitoso! Inicia sesión.")
            return redirect(url_for('login'))
        else:
            flash(f"Error: {msg}")
            
    return render_template('register.html')

# --- RUTA 3: DASHBOARD ---
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    rol = session['rol']
    
    consultores = db.get_consultores_disponibles()
    ganancias = 0 
    reservas = []
    stats = {}

    if rol == 'admin':
        stats = db.obtener_estadisticas_admin()
    elif rol == 'cliente':
        reservas = db.get_reservas_cliente(usuario)
    else: # Consultor
        reservas = db.get_reservas_consultor(usuario)
        ganancias = db.calcular_ganancias_consultor(usuario)
    
    return render_template('dashboard.html', 
                           usuario=usuario, 
                           rol=rol, 
                           consultores=consultores, 
                           reservas=reservas, 
                           ganancias=ganancias,
                           stats=stats,
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

# --- RUTA 5: GESTIONAR CITA (LÓGICA REALISTA MEJORADA) ---
@app.route('/gestionar_cita', methods=['POST'])
def gestionar_cita():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    id_reserva = request.form['id_reserva']
    accion = request.form['accion'] 
    
    # Capturamos el input del usuario (puede ser número o texto)
    texto_input = request.form.get('notas', '') 

    if accion == 'completar':
        # LÓGICA INTELIGENTE:
        # Detectamos si el usuario envió una calificación (número) o una nota (texto)
        try:
            calificacion = int(texto_input)
            # Aseguramos que esté entre 1 y 5
            if calificacion < 1: calificacion = 1
            if calificacion > 5: calificacion = 5
            
            nota_texto = f"Cliente calificó con {calificacion} estrellas."
        except ValueError:
            # Si escribió texto, la calificación numérica es 0 (no aplica)
            calificacion = 0
            nota_texto = texto_input

        # Enviamos: Estado Completada, Calificación Numérica y Texto
        exito, msg = db.actualizar_estado_cita(id_reserva, 'Completada', calificacion=calificacion, notas=nota_texto)
        
    elif accion == 'cancelar':
        # Si se cancela, mandamos 0 calificación y el motivo
        motivo = texto_input if texto_input else "Cancelada por usuario."
        exito, msg = db.actualizar_estado_cita(id_reserva, 'Cancelada', calificacion=0, notas=motivo)
    
    if exito:
        flash(msg)
    else:
        flash(f"Error: {msg}")
        
    return redirect(url_for('dashboard'))

# --- RUTA 6: LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
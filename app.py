from flask import Flask, render_template, request, redirect, url_for, flash, session
from datetime import datetime


try:
    from backend.sistema import SistemaBackend
except ImportError:
    
    from backend.sistema import SistemaBackend

app = Flask(__name__)
app.secret_key = "secreto_super_seguro" 

# Inicializamos la conexión
db = SistemaBackend()

# ==========================================
# RUTA 1: INICIO DE SESIÓN
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        password = request.form['password']
        
        # db.autenticar devuelve (True/False, Rol)
        exito, resultado = db.autenticar(usuario, password)
        
        if exito:
            session['usuario'] = usuario
            session['rol'] = resultado # El rol viene en la segunda posición
            return redirect(url_for('dashboard'))
        else:
            flash("❌ Usuario o contraseña incorrectos.")
            
    return render_template('login.html')

# ==========================================
# RUTA 2: REGISTRO (Adaptado al HTML de tu compañero)
# ==========================================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # 1. Capturamos los datos básicos
        rol = request.form['rol'] # Viene del input hidden
        nombre = request.form['nombre']
        email = request.form['email']
        usuario = request.form['username']
        password = request.form['password']
        
        # 2. Inicializamos variables de consultor en 0/Vacío
        especialidad = "General"
        tarifa = 0
        descripcion = ""
        experiencia_anos = 0 
        primera_cita_descuento = False
        porcentaje_descuento = 0
        
        # 3. Si es consultor, leemos los campos extra
        if rol == 'consultor':
            especialidad = request.form.get('especialidad', 'General')
            try:
                tarifa = float(request.form.get('tarifa', 0))
            except ValueError:
                tarifa = 0
            
            descripcion = request.form.get('descripcion', '')
            
            # TRUCO DE LA Ñ: El HTML manda 'experiencia_años', Python usa 'experiencia_anos'
            try:
                experiencia_anos = int(request.form.get('experiencia_años', 0))
            except ValueError:
                experiencia_anos = 0
            
            # Checkbox: Si está marcado envía 'true' (value del HTML)
            val_checkbox = request.form.get('primera_cita_descuento')
            if val_checkbox == 'true' or val_checkbox == 'on':
                primera_cita_descuento = True
                try:
                    porcentaje_descuento = float(request.form.get('porcentaje_descuento', 0))
                except ValueError:
                    porcentaje_descuento = 0
        
        # 4. Enviamos todo a la base de datos
        exito, msg = db.registrar_usuario(
            usuario, password, nombre, email, 
            rol=rol, 
            especialidad=especialidad, 
            tarifa=tarifa,
            descripcion=descripcion,
            experiencia_anos=experiencia_anos, # Variable limpia sin ñ
            primera_cita_descuento=primera_cita_descuento,
            porcentaje_descuento=porcentaje_descuento
        )
        
        if exito:
            flash(f"✅ ¡Registro exitoso como {rol.capitalize()}! Por favor inicia sesión.")
            return redirect(url_for('login'))
        else:
            flash(f"⚠️ Error: {msg}")
            
    return render_template('register.html')

# ==========================================
# RUTA 3: DASHBOARD (Panel Principal)
# ==========================================
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    rol = session['rol']
    
    # Datos comunes
    consultores = db.get_consultores_disponibles()
    reservas = []
    ganancias = 0 
    stats = {}

    # Lógica según el rol
    if rol == 'admin':
        stats = db.obtener_estadisticas_admin()
    elif rol == 'cliente':
        reservas = db.get_reservas_cliente(usuario)
    else: # Consultor
        reservas = db.get_reservas_consultor(usuario)
        ganancias = db.calcular_ganancias_consultor(usuario)
    
    # Renderizamos pasando 'now' para validar fechas en el HTML
    return render_template('dashboard.html', 
                           usuario=usuario, 
                           rol=rol, 
                           consultores=consultores, 
                           reservas=reservas, 
                           ganancias=ganancias,
                           stats=stats,
                           now=datetime.now())

# ==========================================
# RUTA 4: CREAR CITA (Reserva)
# ==========================================
@app.route('/crear_cita', methods=['POST'])
def crear_cita():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    consultor_nombre = request.form['consultor']
    fecha_html = request.form['fecha']
    
    exito, msg = db.crear_reserva(usuario, consultor_nombre, fecha_html)
    
    if exito:
        flash("✅ ¡Cita reservada con éxito!")
    else:
        flash(f"❌ Error al reservar: {msg}")
        
    return redirect(url_for('dashboard'))

# ==========================================
# RUTA 5: GESTIONAR CITA (Pagar / Cancelar)
# ==========================================
@app.route('/gestionar_cita', methods=['POST'])
def gestionar_cita():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    id_reserva = request.form['id_reserva']
    accion = request.form['accion'] 
    texto_input = request.form.get('notas', '') 

    if accion == 'completar':
        # EL CLIENTE PAGA Y CALIFICA
        try:
            calificacion = int(texto_input)
            # Validamos rango 1-5
            if calificacion < 1: calificacion = 1
            if calificacion > 5: calificacion = 5
            
            nota_texto = f"Cliente calificó con {calificacion} estrellas."
        except ValueError:
            # Si por error mandó texto en vez de número
            calificacion = 5 
            nota_texto = texto_input

        exito, msg = db.actualizar_estado_cita(
            id_reserva, 'Completada', calificacion=calificacion, notas=nota_texto
        )
        
    elif accion == 'cancelar':
        # CUALQUIERA CANCELA (Cliente o Consultor)
        motivo = texto_input if texto_input else "Cancelada por usuario."
        # Al cancelar, la calificación es 0 y el costo baja a 0 (lógica en sistema.py)
        exito, msg = db.actualizar_estado_cita(
            id_reserva, 'Cancelada', calificacion=0, notas=motivo
        )
    
    if exito:
        flash(f"ℹ️ {msg}")
    else:
        flash(f"❌ Error: {msg}")
        
    return redirect(url_for('dashboard'))

# ==========================================
# RUTA 6: CERRAR SESIÓN
# ==========================================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
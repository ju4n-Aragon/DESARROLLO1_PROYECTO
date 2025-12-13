from flask import Flask, render_template, request, redirect, url_for, flash, session
from backend.sistema import SistemaBackend

app = Flask(__name__)
app.secret_key = "secreto_seguro"  # Necesario para usar flash messages y session

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
        
        especialidad = "General"
        tarifa = 0
        
        if rol == 'consultor':
            especialidad = request.form.get('especialidad', 'General')
            try:
                tarifa = float(request.form.get('tarifa', 0))
            except ValueError:
                tarifa = 0
        
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

# --- RUTA 3: DASHBOARD (PANEL PRINCIPAL) ---
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session: return redirect(url_for('login'))
    
    usuario = session['usuario']
    rol = session['rol']
    
    consultores = db.get_consultores_disponibles()
    ganancias = 0  # Variable nueva para el dinero
    
    if rol == 'cliente':
        reservas = db.get_reservas_cliente(usuario)
    else:
        # LÓGICA NUEVA: Si es consultor, traemos reservas Y calculamos dinero
        reservas = db.get_reservas_consultor(usuario)
        ganancias = db.calcular_ganancias_consultor(usuario)
    
    # Enviamos la variable 'ganancias' al HTML
    return render_template('dashboard.html', usuario=usuario, rol=rol, 
                           consultores=consultores, reservas=reservas, ganancias=ganancias)

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
    
    # 1. Recibimos los datos y los imprimimos en la consola (MIRA TU TERMINAL NEGRA)
    id_reserva_str = request.form['id_reserva']
    accion = request.form['accion'] 
    notas = request.form.get('notas', '') 
    
    print(f"--- INTENTANDO ACTUALIZAR ---")
    print(f"ID recibido (Texto): {id_reserva_str}")
    print(f"Acción: {accion}")
    print(f"Notas: {notas}")

    # 2. CONVERSIÓN EXPLÍCITA A NÚMERO (Vital para SQL)
    try:
        id_reserva = int(id_reserva_str)
    except ValueError:
        flash("Error: El ID de la reserva no es válido.")
        return redirect(url_for('dashboard'))

    # 3. Lógica de estados (CUIDADO CON LAS MAYÚSCULAS)
    if accion == 'completar':
        # "Completada" debe ser IDÉNTICO a lo que pusiste en el SQL CHECK
        exito, msg = db.actualizar_estado_cita(id_reserva, 'Completada', notas)
    elif accion == 'cancelar':
        exito, msg = db.actualizar_estado_cita(id_reserva, 'Cancelada', "Cancelada por consultor.")
    
    print(f"Resultado BD: {exito} - {msg}") # Chivato final
    
    if exito:
        flash(msg)
    else:
        flash(f"Error al guardar: {msg}")
        
    return redirect(url_for('dashboard'))

# --- RUTA 6: CERRAR SESIÓN ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
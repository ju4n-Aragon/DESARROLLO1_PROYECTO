import os
from PIL import Image, ImageDraw, ImageFont

# 1. Crear la carpeta 'img' si no existe
if not os.path.exists("img"):
    os.makedirs("img")
    print("Carpeta 'img' creada.")

# 2. Generar 'fondo_login.jpg' (Un gradiente o color sólido elegante)
# Creamos una imagen de 900x650 color Azul Oscuro Corporativo
fondo = Image.new('RGB', (900, 650), color="#2C3E50")
d = ImageDraw.Draw(fondo)
# Dibujamos algunas formas para que no sea plano (Simulación de diseño)
d.rectangle([0, 0, 900, 150], fill="#34495E") # Franja superior
d.rectangle([0, 500, 900, 650], fill="#34495E") # Franja inferior
fondo.save("img/fondo_login.jpg")
print("Imagen 'fondo_login.jpg' generada.")

# 3. Generar 'logo.png' (Un icono simple)
# Imagen transparente de 100x100
logo = Image.new('RGBA', (100, 100), (255, 255, 255, 0))
d = ImageDraw.Draw(logo)
# Dibujamos un círculo azul y una letra "C"
d.ellipse([10, 10, 90, 90], fill="#3498DB", outline=None)


d.rectangle([35, 30, 45, 70], fill="white") # Palito vertical
d.rectangle([35, 30, 65, 40], fill="white") # Palito arriba
d.rectangle([35, 60, 65, 70], fill="white") # Palito abajo

logo.save("img/logo.png")
print("Imagen 'logo.png' generada.")

print("¡Listo! Ya tienes las imágenes en la carpeta 'img'. Ahora corre main.py")
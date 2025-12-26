import streamlit as st
import pandas as pd
import requests
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime
from utils.auth import acceder_google_sheets 
import re


spreadsheet_id_users = st.secrets['ID_DRIVE_USERS']
worksheet_users, df_usuarios = acceder_google_sheets(spreadsheet_id_users)

if 'flag_nombre' not in st.session_state:
    st.session_state.flag_nombre = False
if 'flag_nick' not in st.session_state:    
    st.session_state.flag_nick = False
if 'flag_perfil' not in st.session_state:
    st.session_state.flag_perfil = False
if 'flag_mail' not in st.session_state:
    st.session_state.flag_mail = False
if 'flag_codigo' not in st.session_state:
    st.session_state.flag_codigo = False
if 'codigo_enviado' not in st.session_state:
    st.session_state.codigo_enviado=None

#usar_perfil=True
#flag_codigo=False

def generar_codigo():
    return ''.join(random.choices(string.digits, k=6))

def enviar_codigo_email(destinatario, codigo):
    remitente = "jovidal71@gmail.com"
    contrasena = st.secrets['PASSWORD_GMAIL']
    asunto = "Código de Verificación registro Super Power OMIE"

    # Crear el mensaje
    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje['Subject'] = asunto

    # Cuerpo del mensaje
    cuerpo = f'El código de verificación es: {codigo}'
    mensaje.attach(MIMEText(cuerpo, 'plain'))

    try:
        # Conectar con el servidor SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Establecer conexión segura
        server.login(remitente, contrasena)
        text = mensaje.as_string()
        server.sendmail(remitente, destinatario, text)
        server.quit()
        print("Correo enviado con éxito!")
        return True
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return False

def generar_menu():
     with st.sidebar:
          st.write('Menú')
          st.page_link('pages/main.py',label='Principal', icon=':material/home:')
          
          st.switch_page('pages/main.py')

#ELEMENTOS DEL LAYOUT----------------------------------------------------------------------------------------
st.header('Página de registro')
if st.button('Salir al menu de login'):
    st.switch_page('sp25.py')
a = st.form('registro')
zona_boton_codigo = st.empty()
b = st.form('Introduce el código recibido')

with a:
        st.info('**Instrucciones**\n\n' 
                '1. Introduce tu nombre y primer apellido (**:orange[nombre corto]**). Es el que aparecerá en los listados. Por ejemplo: *Jose Vidal* \n'
                '2. Introduce tu **:orange[nick]**. Será único por usuario y lo usarás para acceder a la app. Por ejemplo: *patodonald* \n'
                '3. Introduce la url de tu perfil de **:orange[Linkedin]**. Debo validar tu perfil ya que la superporra es sólo para esta red. \n'
                '4. Introduce tu **:orange[email]**. Lo usaré para enviarte notificaciones muy concretas, como avisarte de los plazos de apertura y cierre de las minipowers. Por ti y por mí. \n'
                '5. Finalmente, introduce el **:orange[código] recibido en el email de prueba para verificarlo'
                ,icon="ℹ️")
        
        nombre=st.text_input('nombre corto', help='Nombre y primer apellido. Usado para la visualización de datos en la app.', autocomplete='off')
        # eliminamos espacios iniciales y finales (strip)
        # dejamos un solo espacio en medio (split)
        # formateamos tipo Jose Vidal
        nombre = ' '.join(nombre.strip().split()).title()
        mensaje_nombre=st.empty()
        nick=st.text_input('nick', help='Usado para el login.', autocomplete='off')
        nick = nick.strip()

        mensaje_nick=st.empty()
        perfil=st.text_input('url perfil linkedin', help='Usado para evitar usuarios externos.', autocomplete='off')
        perfil = perfil.strip()
        mensaje_perfil=st.empty()
        email=st.text_input('email', help='Usado para notificaciones.', autocomplete='off')
        email = email.strip()
        mensaje_email=st.empty()
        
        boton_comprobar=a.form_submit_button('Comprobar datos')
        mensaje_registro=st.empty()

        

        if boton_comprobar:

            #COMPROBAMOS SI EL NOMBRE CORTO ESTÁ DISPONIBLE
            if nombre in df_usuarios['nombre'].values:
                mensaje_nombre.warning ('El nombre ya está en uso. Por favor elige otro.')
            elif nombre=='':
                mensaje_nombre.error ('Debes introducir un nombre válido (p.e. Jose Vidal)')
            else:
                mensaje_nombre.success('Nombre disponible.') 
                st.session_state.flag_nombre=True 

            #COMPROBAMOS SI EL NICK ESTÁ DISPONIBLE
            if nick in df_usuarios['nick'].values:
                mensaje_nick.warning ('El nick ya está en uso. Por favor elige otro.')
            elif nick=='':
                mensaje_nick.error ('Debes introducir un nick válido (p.e. patodonald)')
            else: 
                mensaje_nick.success ('Nick disponible.')
                st.session_state.flag_nick=True

            #COMPROBAMOS SI EL PERFIL LINKEDIN ES CORRECTO
            if st.session_state.flag_perfil==False: 
                # Expresión regular para validar diferentes variantes de URLs de LinkedIn
                linkedin_regex = r'^(https?:\/\/)(www\.)?([a-z]{0,2}\.)?linkedin\.com\/in\/'
                #linkedin_regex = r'^(https?:\/\/)([a-z]{0,2}\.)?linkedin\.com\/in\/[a-zA-Z0-9\-]+\/?$'    
                if perfil in df_usuarios['perfil'].values:
                    mensaje_perfil.warning ('Perfil Linkedin en uso. Por favor elige otro.')
                elif perfil == '':
                    mensaje_perfil.error ('Por favor introduce un perfil Linkedin (p.e. https://www.linkedin.com/in/jfvidalsierra/)')
                elif perfil == 'url_in':
                    mensaje_perfil.success('Perfil de Linkedin comprobado por la puerta de atrás.')
                    st.session_state.flag_perfil=True
                elif perfil in ['https://www.linkedin.com', 'https://www.linkedin.com/']:
                    #mensaje_perfil.success('Perfil de Linkedin comprobado.')
                    #st.session_state.flag_perfil=True
                    mensaje_perfil.error('Introduce un perfil de usuario!')
                elif re.match(linkedin_regex, perfil):
                    mensaje_perfil.success('Perfil de LinkedIn comprobado.')
                    st.session_state.flag_perfil = True
                    #mensaje_perfil.success('Perfil de Linkedin comprobado.')
                    #st.session_state.flag_perfil=True
                else:
                    mensaje_perfil.error('Introduce un perfil válido de Linkedin')    

            else:
                mensaje_perfil.success('Perfil de Linkedin comprobado.')
                   
            #COMPROBAMOS EL EMAIL DEL USUARIO        
            if email in df_usuarios['email'].values:
                mensaje_email.warning ('Email en uso. Por favor elige otro.')
            elif email=='':
                mensaje_email.warning ('Por favor introduce un email válido')
            else:
                
                st.session_state.flag_mail = True
 
# vamos a lanzar y comprobar el código enviado al email
if st.session_state.flag_nombre and st.session_state.flag_nick and st.session_state.flag_perfil and st.session_state.flag_mail:
    mensaje_registro.success('Parece que todo es correcto. Queda verificar el email mediante el envío de un código!!')
    # enviamos un código y nos asegurarmos de que no se envía otro
    if zona_boton_codigo.button('Generar un nuevo código'):
                st.session_state.codigo_enviado=generar_codigo()
                flag = enviar_codigo_email(email,st.session_state.codigo_enviado)
                st.session_state.flag_codigo = True
       
    with b:
            
            codigo_usuario=st.text_input('Introduce el código que has recibido por correo.',autocomplete='off')
            mensaje_codigo=st.empty()
            boton_codigo=b.form_submit_button('Verificar código')
            if boton_codigo:
                if codigo_usuario==st.session_state.codigo_enviado:
                    mensaje_codigo.success('Código verificado correctamente.')
                    st.session_state.flag_codigo=True
                    ahora=datetime.now()
                    fecha_registro=ahora.strftime('%Y-%m-%d %H:%M:%S')
                    #print(fecha_registro)
                    time.sleep(2)
                    
                    nuevo_usuario=[nombre, nick, perfil, email, fecha_registro]
                    #df_usuarios=pd.concat([df_usuarios, nuevo_usuario], ignore_index=True)
                    #df_usuarios.to_csv(csv_usuarios, index=False)
                    #agregar_usuario(nuevo_usuario)
                    worksheet_users.append_row(nuevo_usuario)
                    mensaje_codigo.success('Registro completado!!')
                    
                    time.sleep(3)
                    st.session_state.clear
                    #st.switch_page('pages/main.py')
                    st.switch_page('sp25.py')
                    st.rerun()
                else:
                    mensaje_codigo.error('Código incorrecto. Por favor, introdúcelo de nuevo.')
else:
    mensaje_registro.error('Por favor comprueba los datos.')    
     




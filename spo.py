import streamlit as st
import time
from datetime import datetime
import pandas as pd
from utils.auth import autenticar_google_sheets
import base64


#configuramos la web y cabecera
st.set_page_config(
    page_title="SuperPowerOMIE",
    page_icon="⚡",
    layout='centered',
    #initial_sidebar_state='collapsed'
)

#autenticamos en google sheets
if 'client' not in st.session_state:
    #client=
    st.session_state.client=autenticar_google_sheets()


#if 'nombre' not in st.session_state:
    #st.session_state.nombre='Invitad@'
st.session_state.get('nombre', None)

st.title(':orange[e]PowerAPP© ⚡️:rainbow[SUPERPOWER]⚡️')
st.subheader('El gran juego de las predicciones OMIE.')
st.caption("Copyright by Jose Vidal 2024-2025:ok_hand:")

with open("images/banner.png", "rb") as f:
    data = f.read()
    encoded = base64.b64encode(data).decode()

# Mostrar la imagen con estilo
st.markdown(f"""
    <style>
        .img-redonda {{
            border-radius: 10px;
            width: 100%;
            height: auto;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
        }}
    </style>
    <img src="data:image/png;base64,{encoded}" class="img-redonda"/>
""", unsafe_allow_html=True)

st.write("")
st.write("")
url_totalpower = "https://epowerapp-totalpower-josevidal.streamlit.app/"
st.write("Visita mi :orange[e]PowerApp [TOTALPOWER](%s) con un montón de utilidades." % url_totalpower)
#url_linkedin = "https://www.linkedin.com/posts/jfvidalsierra_powerapps-activity-7216715360010461184-YhHj?utm_source=share&utm_medium=member_desktop"
#st.write("Deja tus comentarios y propuestas en mi perfil de [Linkedin](%s)." % url_linkedin)
#url_bluesky = 'https://bsky.app/profile/poweravenger.bsky.social'
#url_linkedin = 'https://www.linkedin.com/in/jfvidalsierra/'
#st.markdown("¡Sígueme en [Linkedin](https://www.linkedin.com/in/jfvidalsierra/) y en [Bluesky](https://bsky.app/profile/poweravenger.bsky.social)!")
#Visita mi perfil de [Linkedin](%s) para resolver cualquier duda o incidencia con la aplicación.' % url_linkedin
#st.write("Visita mi perfil de [Linkedin](%s) y disfruta del mejor contenido energético." % url_linkedin)
st.markdown("Visita mi perfil de [LinkedIn](https://www.linkedin.com/in/josefvidalsierra/) y disfruta del mejor contenido.")

st.info('Bienvenido a la :orange[e]PowerApp **:rainbow[SuperpowerOMIE]**, donde podrás poner a prueba tus habilidades como gurú de la energía.', icon="ℹ️")
st.warning('Atención: Todo el mundo debe registrarse (primera opción), aunque hayas participado en la SUPERPORRAOMIE2024!!',icon="⚠️")
alta_usuario=st.button('Soy nuevo y me quiero registrar',type='primary', use_container_width=True) #, disabled=True)
usuario_registrado=st.button('Ya estoy registrado y quiero entrar', type='primary',use_container_width=True) #, disabled=True)     
usuario_demo=st.button('Entrar como invitado en modo demo', type='primary',use_container_width=True)     


if alta_usuario:
    st.switch_page('pages/registro.py')

if usuario_registrado:
    st.switch_page('pages/login.py')

if usuario_demo:
    st.session_state.nombre = 'Invitad@'
    st.success('¡Bienvenid@ a la SuperpowerOMIE!')
    time.sleep(2)
    st.switch_page('pages/main.py')
    





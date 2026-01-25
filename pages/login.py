import streamlit as st
import pandas as pd
import time
from utils.auth import acceder_google_sheets, autenticar_google_sheets
from streamlit_cookies_manager import EncryptedCookieManager


spreadsheet_id_users = st.secrets['ID_DRIVE_USERS']

cookies = EncryptedCookieManager(
     prefix = 'login_',
     password='pass_vidal'
)

if not cookies.ready():


    st.stop()

nick_predeterminado = cookies.get('nick','')

if 'nombre' not in st.session_state:
    #st.session_state.nombre='Invitad@'
    st.session_state.nombre = None

if 'client' not in st.session_state:
    #client=
    st.session_state.client=autenticar_google_sheets()

st.header('Página de login')

if st.button('Salir al menu de login'):
    st.switch_page('spo.py')
if st.session_state.nombre is None:
    with st.form('Login'):
        
        nick=st.text_input('nick',value=nick_predeterminado, autocomplete='off', type='password') #usar password más adelante. no usarlo ahora facilita las pruebas
        boton_logear=st.form_submit_button('logear')

        if boton_logear:
        
            worksheet, df_usuarios = acceder_google_sheets(spreadsheet_id_users)
            
            if nick in df_usuarios['nick'].values:
            #if nick.lower() in df_usuarios['nick'].str.lower().values:                
                #fila = df_usuarios.loc[df_usuarios['nick'].str.lower() == nick.lower()]
                #st.session_state.nombre = fila['nombre'].values[0]
                st.session_state.nombre = df_usuarios.loc[df_usuarios['nick'] == nick, 'nombre'].values[0]
                cookies['nick'] = nick
                #st.write(cookies)
                st.success(f'¡Bienvenid@ {st.session_state.nombre}!')
                time.sleep(2)
                st.switch_page('pages/main.py')
            else:
                st.error ('No existe ese nick. Por favor introdúcelo de nuevo.')
else:
    st.success(f'¡Bienvenid@ {st.session_state.nombre}!')
    time.sleep(2)
    st.switch_page('pages/main.py')
                
                
                



#    
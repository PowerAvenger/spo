import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st


#ESTE CÓDIGO ES PARA PERMITIR EL ACCESO A LOS GOOGLE SHEETS DEL DRIVE
def autenticar_google_sheets():
    # Rutas y configuraciones
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    #CREDENTIALS_FILE = 'spo25-442409-dbdb74d35fae.json'  
    CREDENTIALS_FILE = st.secrets['GOOGLE_SHEETS_CREDENTIALS']
    # Autenticación
    #credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    credentials = Credentials.from_service_account_info(CREDENTIALS_FILE, scopes=SCOPES)
    st.session_state.client = gspread.authorize(credentials)

    # Acceso a la hoja de Google Sheets
    #SPREADSHEET_ID = '1kvtwjmvUhNjHlnA6nS9BI0ExwC8czTina-b4zBLcWVM'  # Cambia esto por el ID de tu archivo (en la URL después de /d/)
    #sheet = client.open_by_key(SPREADSHEET_ID)

    # Acceder a una hoja específica dentro del archivo
    #worksheet = sheet.sheet1  # Primera hoja
    #data = worksheet.get_all_records()
    #df_usuarios=pd.DataFrame(data)
    #return worksheet, df_usuarios
    return st.session_state.client


#ESTE CÓDIGO ES PARA ACCEDER A LOS DIFERENTES SHEETS - TODO EL CONTENIDO
def acceder_google_sheets(spreadsheet_id): 
    
    sheet = st.session_state.client.open_by_key(spreadsheet_id)
    
    # Primera hoja por defecto
    worksheet = sheet.sheet1  
    # Obtener los datos como DataFrame
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return worksheet, df

def acceder_google_sheets_parcial(spreadsheet_id): 
    """
    MONTAMOS UN DF EXTRAIDO DE SHEETS TELEMINDEX CON LA ESTRUCTURA SIMILAR AL DF OMIE DE ESIOS API REE
    """
    sheet = st.session_state.client.open_by_key(spreadsheet_id)
    
    # Primera hoja por defecto
    worksheet = sheet.sheet1  
    # Obtener los datos como DataFrame
    col_A = worksheet.col_values(1)  # fecha
    col_B = worksheet.col_values(2) #año 
    col_C = worksheet.col_values(3) #mes
    col_I = worksheet.col_values(9)  # spot
    # Une en DataFrame
    df = pd.DataFrame({'datetime': col_A[1:], 'omie': col_I[1:], 'mes': col_C[1:], 'año': col_B[1:]})  # col_A[0] es encabezado

    # Procesa como antes
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    df['omie'] = pd.to_numeric(df['omie'], errors='coerce')
    df['año'] = pd.to_numeric(df['año'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
    df_filtrado = df[df['datetime'].dt.year >= 2024]
    
    return worksheet, df_filtrado

if 'client' not in st.session_state:
    #client=
    st.session_state.client=autenticar_google_sheets()
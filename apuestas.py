import pandas as pd
import streamlit as st
import requests
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from utils.auth import acceder_google_sheets, acceder_google_sheets_parcial
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import locale


# OBTENEMOS DATOS DE LAS APUESTAS DEL GOOGLE SHEETS
# Retornamos el listado de apuestas y lista de participantes para el mes seleccionado por el usuario
def obtener_apuestas():
    df_apuestas_select = st.session_state.df_apuestas[st.session_state.df_apuestas['mes_apuesta'] == st.session_state.mes_miniporra_select]
    
    #añadimos el valor de omip last3 m-1
    df_omip = pd.DataFrame([{
        'mes_apuesta': st.session_state.mes_miniporra_select,   # o la variable que corresponda
        'nombre': 'OMIP',
        'apuesta': st.session_state.omip
    }])
    df_apuestas_select = pd.concat([df_apuestas_select, df_omip], ignore_index=True)
    df_apuestas_select = df_apuestas_select.sort_values(by = 'apuesta', ascending = False, ignore_index = True)
    df_apuestas_select = df_apuestas_select.drop(columns = 'fecha_apuesta')

    star_powers = st.session_state.df_apuestas['nombre'].unique().tolist()

    print ('df_apuestas_select')
    print (df_apuestas_select)

    return  df_apuestas_select, star_powers 


@st.cache_data
def download_esios_id(id, fecha_ini, fecha_fin, agrupacion):
        
    token = st.secrets['ESIOS_API_KEY']
    cab = {
        'User-Agent': 'Mozilla/5.0',
        'x-api-key' : token
    }
    url_id = 'https://api.esios.ree.es/indicators'
    url=f'{url_id}/{id}?geo_ids[]=3&start_date={fecha_ini}T00:00:00&end_date={fecha_fin}T23:59:59&time_trunc={agrupacion}&time_agg=average'
    print(url)
    response = requests.get(url, headers=cab)
    #print(response.status_code, response.text)
    #datos_origen = requests.get(url, headers=cab).json()
    datos_origen = response.json()
    
    datos=pd.DataFrame(datos_origen['indicator']['values'])
    datos = (datos
        .assign(datetime=lambda vh_: pd #formateamos campo fecha, desde un str con diferencia horaria a un naive
            .to_datetime(vh_['datetime'],utc=True)  # con la fecha local
            .dt
            .tz_convert('Europe/Madrid')
            .dt
            .tz_localize(None)
            ) 
        )
    #dataframe con los valores horarios de las tecnologias
    #lo mezclamos con el spot horario
    df_spot = datos.copy()
    df_spot = df_spot.loc[:,['datetime','value']]
    #df_spot['fecha']=df_spot['datetime'].dt.date
    #df_spot['hora']=df_spot['datetime'].dt.hour
    df_spot['mes'] = df_spot['datetime'].dt.month
    df_spot['año'] = df_spot['datetime'].dt.year
    #df_spot.set_index('datetime', inplace=True)
    #df_spot['hora']+=1
    #df_spot['fecha'] = pd.to_datetime(df_spot['fecha']).dt.date
    df_spot=df_spot.rename(columns = {'value':'omie'})
    df_spot['omie'] = df_spot['omie'].round(2)
    print('df_spot')
    print(df_spot)
    
    return df_spot 

@st.cache_data
def obtener_omie_horario_sheets():
    spreadsheet_id_telemindex = st.secrets['ID_DRIVE_TELEMINDEX']
    ws, df_horario = acceder_google_sheets_parcial(spreadsheet_id_telemindex)
    df_omie_diario = df_horario.groupby('datetime').agg({
        'omie':'mean',
        'año': 'first',
        'mes' : 'first'
    }).reset_index()
    print('df omie diario sheets')
    #print(df_omie_diario)
    return df_omie_diario

@st.cache_data
def obtener_omie_diario(): 

    try:
        with st.spinner('Cargando datos desde históricos...'):
            df_omie_diario = obtener_omie_horario_sheets()
    except:
        
        with st.spinner('Cargando datos desde esios REE...'):
            df_omie_diario = download_esios_id('600', '2024-01-01', '2026-12-31', 'day')
        
        

    meses = {1: 'ene', 2: 'feb', 3: 'mar', 4: 'abr', 5: 'may', 6: 'jun', 7: 'jul', 8: 'ago', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dic'}
    df_omie_diario['Entrega'] = df_omie_diario['mes'].map(meses)
    df_omie_diario['Entrega'] = df_omie_diario['Entrega'] + '-' + df_omie_diario['año'].astype(str).str[-2:]
    df_omie_diario['dia'] = df_omie_diario['datetime'].dt.day

    meses_miniporra = df_omie_diario['Entrega'].unique().tolist()
    print('df_omie_diario')
    print(df_omie_diario)
    print(meses_miniporra)

    return df_omie_diario, meses_miniporra
    
# los resultados mensuales se usan en la clasificación anual. Se selecciona el año de la spo
# año_spo son las dos últimas cifras del año, 24 ó 25
def resultados_mensuales(df_omie_diario, año_spo, combo_omip):

    meses_personalizados = [
        "ene-24", "feb-24", "mar-24", "abr-24", "may-24", "jun-24",
        "jul-24", "ago-24", "sep-24", "oct-24", "nov-24", "dic-24",
        "ene-25", "feb-25", "mar-25", "abr-25", "may-25", "jun-25",
        "jul-25", "ago-25", "sep-25", "oct-25", "nov-25", "dic-25",
        "ene-26", "feb-26", "mar-26", "abr-26", "may-26", "jun-26",
        "jul-26", "ago-26", "sep-26", "oct-26", "nov-26", "dic-26"
    ]

    #df_omie_diario = obtener_omie_diario()
    df_omie_mensual = df_omie_diario.groupby('Entrega').agg({
        'omie':'mean',
        #'Entrega':'first'
        }).reset_index()
    df_omie_mensual['omie'] = round(df_omie_mensual['omie'], 2)
    df_omie_mensual = df_omie_mensual.rename(columns = {'Entrega' : 'mes_apuesta'})
    df_omie_mensual['mes_apuesta'] = pd.Categorical(df_omie_mensual['mes_apuesta'], categories = meses_personalizados, ordered = True)
    df_omie_mensual = df_omie_mensual.sort_values('mes_apuesta')
    print('df_omie_mensual')
    print(df_omie_mensual)
    #print(df_omie_mensual.dtypes)
    #print(df_omie_mensual.head())

    #usado para el año seleccionado de la superpoweromie
    df_omie_mensual_spo = df_omie_mensual.copy()
    df_omie_mensual_spo = df_omie_mensual_spo[df_omie_mensual_spo['mes_apuesta'].str.endswith(año_spo)]
    
    # creamos un df tipo lista con todas las apuestas de las minipowers
    df_ranking_mensual = st.session_state.df_apuestas.copy()
    df_ranking_mensual = pd.merge(st.session_state.df_apuestas, df_omie_mensual, on = 'mes_apuesta', how = 'inner')


    

    
    #ranking mensual con todos los meses desde ene-24 hasta la actual minipower
    df_ranking_mensual['desvio'] = df_ranking_mensual['apuesta'] - df_ranking_mensual['omie']
    df_ranking_mensual['desvio_%']=abs(df_ranking_mensual['desvio']/df_ranking_mensual['omie'])*100

    df_ranking_mensual['posicion'] = df_ranking_mensual.groupby('mes_apuesta')['desvio_%'].rank(method='first', ascending=True).astype(int)
    if st.session_state.nombre is not None:
        df_ranking_mensual_nombre = df_ranking_mensual[df_ranking_mensual['nombre'] == st.session_state.nombre]
        df_ranking_mensual_nombre = df_ranking_mensual_nombre.drop(columns = ['nombre', 'fecha_apuesta'])
       
    df_ranking_mensual = df_ranking_mensual.drop(columns=['omie', 'fecha_apuesta'])

    print('df ranking mensual')
    print(df_ranking_mensual)
       
    #creamos un df filas = meses apuesta tipo ene-24 y en las columnas 1, 2 y 3 podio ganador
    df_ranking_mensual_podio = df_ranking_mensual[df_ranking_mensual['posicion'].isin([1,2,3])].pivot(
        index='mes_apuesta', columns='posicion', values='nombre'
    ).reset_index()
    
    #orden_meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    #meses_ordenados = [f'{m}-{año_spo}' for m in orden_meses]
    df_ranking_mensual_podio['mes_apuesta'] = pd.Categorical(df_ranking_mensual_podio['mes_apuesta'], categories=meses_personalizados, ordered=True)
    df_ranking_mensual_podio = df_ranking_mensual_podio.sort_values('mes_apuesta')

    #print(df_ranking_mensual_podio)
    
    # df de rankings según el AÑO SELECCIONADO, usado para la clasificacion general y las comparativas
    df_ranking_mensual_spo = df_ranking_mensual[df_ranking_mensual['mes_apuesta'].str.endswith(año_spo)]
    # creamos un df tipo tabla  (meses tipo ene-24 en las columnas, participantes en filas) con todas las apuestas del año seleccionado
    df_acum_porc = df_ranking_mensual_spo.pivot(index = 'nombre', columns = 'mes_apuesta', values = 'desvio_%')
    df_acum_porc['contar'] = df_acum_porc.notna().sum(axis = 1)

    print('df_acum_porc')
    print (df_acum_porc)

    #tabla con los starpowers y los desvíos de la apuesta sobre omie por meses de la spo. 
    #positivo es que la apuesta fue mayor que omie. negativo que fue menor
    #si es mayor, palmas pasta. si es menor, es ganancia
    df_acum_desvio = df_ranking_mensual_spo.pivot(index = 'nombre', columns = 'mes_apuesta', values = 'desvio')
    df_acum_desvio['contar'] = df_acum_desvio.notna().sum(axis = 1)
    
    print('df_acum_desvio')
    #print (df_acum_desvio)

    #df usado para los payoff-------------------------------------------------------------------------------------
    df_payoff = df_omie_mensual_spo.copy()
    df_payoff['omip'] = df_payoff['mes_apuesta'].map(combo_omip)
    df_payoff = pd.merge(st.session_state.df_apuestas, df_payoff, on = 'mes_apuesta', how = 'inner')
    df_payoff = df_payoff.drop(columns=['fecha_apuesta'])

    horas_meses = {
        'ene-24': 744, 'feb-24': 696, 'mar-24': 744, 'abr-24': 720,
        'may-24': 744, 'jun-24': 720, 'jul-24': 744, 'ago-24': 744,
        'sep-24': 720, 'oct-24': 744, 'nov-24': 720, 'dic-24': 744,

        'ene-25': 744, 'feb-25': 672, 'mar-25': 744, 'abr-25': 720,
        'may-25': 744, 'jun-25': 720, 'jul-25': 744, 'ago-25': 744,
        'sep-25': 720, 'oct-25': 744, 'nov-25': 720, 'dic-25': 744,

        'ene-26': 744, 'feb-26': 672, 'mar-26': 744, 'abr-26': 720,
        'may-26': 744, 'jun-26': 720, 'jul-26': 744, 'ago-26': 744,
        'sep-26': 720, 'oct-26': 744, 'nov-26': 720, 'dic-26': 744
        }
    
    df_payoff['horas_mes'] = df_payoff['mes_apuesta'].map(horas_meses)
    df_payoff['coste_omie'] = df_payoff['horas_mes'] * df_payoff['omie']
    df_payoff['coste_omip'] = df_payoff['horas_mes'] * df_payoff['omip']

    df_payoff['payoff_consumidor'] = df_payoff['coste_omie'] - df_payoff['coste_omip']

    df_payoff['payoff_jugador'] = np.where(df_payoff['apuesta'] < df_payoff['omip'],0, df_payoff['payoff_consumidor'])

    meses_presentes = df_payoff['mes_apuesta'].unique().tolist()
    meses_ordenados = [m for m in meses_personalizados if m in meses_presentes]   
    df_payoff['mes_apuesta'] = pd.Categorical(df_payoff['mes_apuesta'], categories=meses_ordenados, ordered=True)

    print('df payoff')
    print(df_payoff)



    df_payoff_mensual = (
        df_payoff
        .pivot_table(
            index='nombre',
            columns='mes_apuesta',
            values='payoff_jugador',
            aggfunc='sum',      # por si hubiera más de una apuesta por mes
            fill_value=0
        )
    )

    #meses_unicos = df_payoff['mes_apuesta'].unique().tolist()
    #orden_meses = sorted(df_payoff['mes_apuesta'].unique())
    #df_payoff_mensual = df_payoff_mensual[orden_meses]
    df_payoff_mensual['Total'] = df_payoff_mensual.sum(axis=1)

    print('df payoff mensual')
    print(df_payoff_mensual)

    df_payoff_mensual_format = df_payoff_mensual.copy()
    columnas_a_formatear = [col for col in df_payoff_mensual_format.columns if col in horas_meses or col == "payoff_jugador" or col=='Total']
    df_payoff_mensual_format[columnas_a_formatear] = df_payoff_mensual_format[columnas_a_formatear].applymap(lambda x: f"{x:,.0f}".replace(",", "."))

    def color_texto(val):
        if isinstance(val, str):
            num = float(val.replace(".", ""))
            if num > 0:
                return "color: lightgreen; font-weight: bold;"
            elif num < 0:
                return "color: red; font-weight: bold;"
            else:
                return "color: black;"
        return ""

    # Aplicar formato de colores a las columnas de meses y payoff
    df_payoff_mensual_format = df_payoff_mensual_format.style.applymap(color_texto, subset=columnas_a_formatear)

    print ('df_payoff_mensual_format')
    print (df_payoff_mensual_format)
   
    return df_ranking_mensual_spo, df_acum_porc, df_omie_mensual, df_omie_mensual_spo, df_ranking_mensual_podio, df_ranking_mensual_nombre, df_payoff_mensual_format


def obtener_omie_omip(df_omie_mensual, combo_omip):
    df_omie_omip = df_omie_mensual.copy()
    
    df_omie_omip['omip'] = df_omie_omip['mes_apuesta'].map(combo_omip)
    print('df_omie_omip')
    print (df_omie_omip) 
    print("Dtypes justo antes de la resta:")
    print(df_omie_omip.dtypes)
    df_omie_omip['omip'] = pd.to_numeric(df_omie_omip['omip'], errors='coerce')
    df_omie_omip['dif'] = df_omie_omip['omip'] - df_omie_omip['omie']
    df_omie_omip['dif%'] = df_omie_omip['dif'] * 100 / df_omie_omip['omie']
    df_omie_omip['dif%_abs'] = df_omie_omip['dif%'].abs()
    
    print('df_omie_omip')
    print (df_omie_omip)    

    return df_omie_omip

def grafico_omie_omip(df_omie_omip):

    grafico_omie_omip = px.bar(df_omie_omip, x = 'mes_apuesta', y = ['omie', 'omip'],
        #color='nombre',
        barmode = 'group',
        color_discrete_map = {'omip':'violet', 'omie':'orange'},
        #text_auto = True,
        #text = 'media_texto',
        labels = {'value': '€/MWh'},
        #title=f'Comparativa de {nombre_seleccionado} contra OMIP',
        
    )

    colores_dif = ['red' if var >= 0 else 'green' for var in df_omie_omip['dif']]

    grafico_omie_omip.add_trace(go.Bar(
        x = df_omie_omip['mes_apuesta'],
        y = df_omie_omip['dif'],
        name = 'dif',
        marker_color = colores_dif,
        offset = -0.1

    ))   
    grafico_omie_omip.update_layout(
        bargap = .4,
        legend = {'title':''},
        font = dict(color = 'white'),
        title = dict(
            text = f'Comparativa de OMIP vs OMIE.',
            x = .5,
            xanchor = 'center',
            ),
        #barmode = 'group'
        
    )
    grafico_omie_omip.update_traces(
        width = .2,
        textangle = 45,
        
        #texttemplate='%{text:.2f}',  # Formato de los valores (2 decimales)
        textfont=dict(
            family='Arial, sans-serif',
                # Tipo de fuente
            #size=16,  # Tamaño de la fuente
            #color='black',  # Color de la fuente
            #weight='bold'  # Negrita
        ),
        textposition = 'outside'
    )

    return grafico_omie_omip



def obtener_clasificacion_porc(df_acum_porc, año_spo):
    
    df_porra_desvios_porc = df_acum_porc.copy()
    df_porra_desvios_porc = df_porra_desvios_porc.reset_index()
    #contamos los meses que llevamos jugando
    num_meses_porra = sum(año_spo in col for col in df_porra_desvios_porc.columns)
    print(f'numero meses porra = {num_meses_porra}')
    #pasamos a numericos los datos de 'contar', para poder filtrar las que nos interesan
    df_porra_desvios_porc['contar'] = df_porra_desvios_porc['contar'].apply(pd.to_numeric, errors='coerce')
    



    #eliminamos aquellos participantes que llevan meses porra menos 2
    if num_meses_porra > 3:
        if st.session_state.doce_meses:
           df_porra_desvios_porc = df_porra_desvios_porc[df_porra_desvios_porc['contar'] == num_meses_porra]
        else:
           df_porra_desvios_porc = df_porra_desvios_porc[df_porra_desvios_porc['contar'] >= num_meses_porra - 2]
    
    #eliminamos espacios en los nombres de las columnas (por si acaso)
    df_porra_desvios_porc.columns = df_porra_desvios_porc.columns.str.strip()
    #print(df_porra_desvios_porc)

    #meses_ordenados = ['ene-24', 'feb-24', 'mar-24', 'abr-24', 'may-24', 'jun-24', 
    #               'jul-24', 'ago-24', 'sep-24', 'oct-24', 'nov-24', 'dic-24']
    meses_base = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 
                  'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    # Generar la lista completa con el sufijo del año
    meses_ordenados = [f"{mes}-{año_spo}" for mes in meses_base]
    #creamos una lista con los nombres de las columnas de los meses del excel acum porc
    li_meses_porra_no_ordenado = [col for col in df_porra_desvios_porc.columns if año_spo in col]
    # Ordenar las columnas según el formato de mes (mes-año)
    li_meses_porra = [mes for mes in meses_ordenados if mes in li_meses_porra_no_ordenado]
    #print (li_meses_porra)
    #obtenemos el último mes
    ultimo_mes_porra = li_meses_porra[-1]
    print(f'Último mes porra: {ultimo_mes_porra}')

    df_porra_desvios_porc = df_porra_desvios_porc.loc[:, ['nombre'] + li_meses_porra]
    #print(df_porra_desvios_porc)
    #df_porra_desvios_porc=df_porra_desvios_porc[['nombre']+li_meses_porra]
    #convertimos los valores de los desvíos% de todos los meses en numericos
    df_porra_desvios_porc[li_meses_porra] = df_porra_desvios_porc[li_meses_porra].apply(pd.to_numeric, errors='coerce')
    #print(df_porra_desvios_porc)
    #print (df_porra_desvios_porc)

    def eliminar_valores_mas_altos(row):
        # Filtrar solo los valores válidos (no NaN)
        valores_validos = row.dropna()
        num_validos = len(valores_validos)
        
        # Definir cuántos valores eliminar
        if num_validos > num_meses_porra - 2:
            # Calcular cuántos valores eliminar para dejar n-2
            eliminar_count = num_validos - (num_meses_porra-2)
            
            # Obtener los valores más altos a eliminar
            top_n = valores_validos.nlargest(eliminar_count)
            
            # Reemplazar esos valores con NaN
            return row.apply(lambda x: np.nan if x in top_n.values else x)
        else:
            # Si hay 7 o menos válidos, no eliminamos nada
            return row

    #eliminamos los valores más altos de cada participante
    if num_meses_porra > 3:
        if not st.session_state.doce_meses:
            df_porra_desvios_porc[li_meses_porra] = df_porra_desvios_porc[li_meses_porra].apply(eliminar_valores_mas_altos, axis=1)
    #print(df_porra_desvios_porc)

    #añadimos columna con la suma y la media de los mejores resultados
    df_porra_desvios_porc['Suma'] = df_porra_desvios_porc.iloc[:, 1:].sum(axis=1, skipna=True)
    df_porra_desvios_porc['Media'] = df_porra_desvios_porc.iloc[:, 1:-1].mean(axis=1, skipna=True)
    #pasamos a numericos los valores de suma y media
    df_porra_desvios_porc[['Suma','Media']] = df_porra_desvios_porc[['Suma','Media']].apply(pd.to_numeric, errors='coerce')
    df_porra_desvios_porc = df_porra_desvios_porc.sort_values(by = 'Media')

    print ('df_porra_desvios_porc')
    print (df_porra_desvios_porc)
    
    #generamos una lista de participantes
    lista_starpowers=df_porra_desvios_porc['nombre'].unique().tolist()
    num_starpowers=len(lista_starpowers)

    return df_porra_desvios_porc, lista_starpowers, num_starpowers, ultimo_mes_porra, num_meses_porra


def grafico_clasificacion(df_porra_desvios_porc):
    graf_clasificacion=px.bar(df_porra_desvios_porc, x='Media',y='nombre',
                            orientation='h',
                            height=800,
                            color='Media',
                            #color_continuous_scale='Viridis',
                            color_continuous_scale=px.colors.sequential.Electric_r,
                            text_auto=False,
                            labels={'Media':'Desvío medio en %'}
                            
                            )

    graf_clasificacion.update_layout(
        showlegend=False,
        margin=dict(l=250),
        bargap=.5,
        coloraxis_showscale=False
        
    )

    graf_clasificacion.update_yaxes(
        autorange="reversed",
        title='',
        tickfont=dict(size=12)
        )

    graf_clasificacion.update_traces(
        width=.7,
        texttemplate='%{x:.3f}', textposition='inside'
    )

    
    return graf_clasificacion    

def obtener_comparativa(nombre_seleccionado, df_porra_desvios_porc, df_omie_omip, num_meses_porra, entrega, año_spo):
    
    #mini df con una fila que el nombre seleccionado
    df_nombre_seleccionado = df_porra_desvios_porc[df_porra_desvios_porc['nombre'] == nombre_seleccionado]
    #print (df_nombre_seleccionado)
    

    #estos son los valores de los desvíos de OMIP frente a OMIE, por meses y en lista
    df_omie_omip = df_omie_omip[df_omie_omip['mes_apuesta'].str.endswith(año_spo)]
    li_desvios_porc_omip = df_omie_omip['dif%_abs'].dropna().to_list()
    
    #print(li_desvios_porc_omip)
    li_desvios_porc_omip = li_desvios_porc_omip[:num_meses_porra]
    
    
    #esta fila se añade al nombre seleccionado
    li_desvios_porc_omip = ['omip'] + li_desvios_porc_omip +['']+['']
    #convertimos a dataframe
    df_desvios_porc_omip = pd.DataFrame([li_desvios_porc_omip], columns=df_nombre_seleccionado.columns)
    print('df_desvios_porc_omip')
    print(df_desvios_porc_omip)
    df_comp_nombre_omip=pd.concat([df_nombre_seleccionado,df_desvios_porc_omip], ignore_index=True)
    #localizamos las columnas del nombre con NaN
    columns_with_nan = df_comp_nombre_omip.iloc[0].isna()
    #Convertimos a NaN los valores de las columnas None del nombre
    #print(df_comp_nombre_omip)
    df_comp_nombre_omip.loc[1, columns_with_nan] = np.nan
    #print(df_comp_nombre_omip)
    df_comp_nombre_omip.iloc[:, 1:num_meses_porra] = df_comp_nombre_omip.iloc[:, 1:num_meses_porra].apply(pd.to_numeric, errors='coerce')
    df_comp_nombre_omip.loc[df_comp_nombre_omip['nombre']=='omip','Suma'] = df_comp_nombre_omip.iloc[1, 1:num_meses_porra].sum(skipna=True)
    df_comp_nombre_omip.loc[df_comp_nombre_omip['nombre']=='omip','Media'] = df_comp_nombre_omip.iloc[1, 1:num_meses_porra].mean(skipna=True)
    df_comp_nombre_omip[['Suma','Media']] = df_comp_nombre_omip[['Suma','Media']].apply(pd.to_numeric, errors='coerce')

    def calcular_suma_media(df, mes_inicio, mes_fin):
        # Seleccionar las columnas entre el mes de inicio y el mes de fin
        columnas_meses = df.columns.get_loc(mes_inicio),df.columns.get_loc(mes_fin) + 1
        #print (columnas_meses)
        df.loc[:,'Suma'] = df.iloc[:,columnas_meses[0]:columnas_meses[1]].sum(axis=1,skipna=True) 
        df.loc[:, 'Media'] = df.iloc[:, columnas_meses[0]:columnas_meses[1]].mean(axis=1, skipna=True)   # Crear nuevas columnas con la suma y la media ignorando los NaN
        columnas_a_conservar = ['nombre']+list(df.columns[columnas_meses[0]:columnas_meses[1]]) + ['Suma', 'Media']
        df = df[columnas_a_conservar]
        return df, columnas_meses

    mes_inicio = f'ene-{año_spo}'
    #entrega = 'Ago 2024'  
    #mes_fin = entrega.capitalize()

    
    df_comp_nombre_omip_din, columnas_meses = calcular_suma_media(df_comp_nombre_omip, mes_inicio, entrega)

    #obtenemos df para graficar en barras las comparativas mensuales, suma y media de los desvios en %
    #del jugador vs omip
    df_comp_nombre_omip_melted=df_comp_nombre_omip_din.melt(id_vars=['nombre'],
                                          var_name='Mes',
                                          value_name='Valor')
    df_comp_nombre_omip_melted['Valor']=df_comp_nombre_omip_melted['Valor'] #*100
    df_comp_nombre_omip_melted['Valor']=df_comp_nombre_omip_melted['Valor'].round(1)
    #df_comp_nombre_omip_melted['media_texto'] = df_comp_nombre_omip_melted['Valor'].apply(lambda x: None if np.isnan(x) else x)
    df_comp_nombre_omip_melted['media_texto'] = df_comp_nombre_omip_melted['Valor'].apply(
        lambda x: str(x) if not np.isnan(x) else None
    )
    media_jugador=df_comp_nombre_omip_melted.iloc[-2,-2]
    media_omip=df_comp_nombre_omip_melted.iloc[-1,-2]
    df_comp_nombre_omip_melted = df_comp_nombre_omip_melted.drop(df_comp_nombre_omip_melted.index[-4:-2])
    print ('df para comparativa contra OMIP')
    print( df_comp_nombre_omip_melted)
    return df_comp_nombre_omip_melted, media_jugador, media_omip


def grafico_comparativo(df_comp_nombre_omip_melted, nombre_seleccionado):

    graf_comp=px.bar(df_comp_nombre_omip_melted, x='Mes', y='Valor',
        color='nombre',
        barmode='group',
        color_discrete_map={'omip':'violet',f'{nombre_seleccionado}':'orange'},
        text_auto=True,
        text='media_texto',
        labels={'Valor': 'Desvío en %'},
        #title=f'Comparativa de {nombre_seleccionado} contra OMIP',
        
    )   
    graf_comp.update_layout(
        bargap=.4,
        legend={'title':''},
        font=dict(color='white'),
        title=dict(
            text=f'Comparativa de {nombre_seleccionado} contra OMIP. Valores en %',
            x=.5,
            xanchor='center',
            )
        
    )
    graf_comp.update_traces(
        width=.2,
        textangle=0,
        
        #texttemplate='%{text:.2f}',  # Formato de los valores (2 decimales)
        textfont=dict(
            family='Arial, sans-serif',
                # Tipo de fuente
            #size=16,  # Tamaño de la fuente
            #color='black',  # Color de la fuente
            #weight='bold'  # Negrita
        ),
        textposition='outside'
    )

    for trace in graf_comp.data:
        trace.text = [t if t is not None else '' for t in trace.text]

    

    return graf_comp

# ESTA FUNCIÓN ES PARA FILTRAR OMIE DIARIO POR EL MES DE LA APUESTA: USADO EN EL APARTADO MINIPOWER-------------------------------------------------------------------------------------------------------
def filtrar_mes_apuesta(df_omie_diario):
    #df_omie_diario = obtener_omie_diario()
    # Filtramos por el mes seleccionado por el usuario
    df_omie_mes_apuesta = df_omie_diario[df_omie_diario['Entrega'] == st.session_state.mes_miniporra_select].copy()
    # Creamos una nueva columna 'omie_media' con la media de omie según avanzan los dias
    df_omie_mes_apuesta['omie_media'] = round(df_omie_mes_apuesta['omie'].expanding().mean(), 2)
    # Obtenemos la fecha del último registro de omie
    ultimo_registro_omie = df_omie_mes_apuesta['datetime'].iloc[-1].date()

    print('df_omie_mes_apuesta')
    print(df_omie_mes_apuesta)
    #print(ultimo_registro) 

        
    return ultimo_registro_omie, df_omie_mes_apuesta

# Obtención de dfs y variables para la minipower en curso: USADO EN EL APARTADO MINIPOWER-----------------------------------------------------------------------
def resultados(df_omie_mes_apuesta): #, dia_seleccion):
    #la media omie hasta el último día registrado
    media_omie = round(df_omie_mes_apuesta['omie'].mean(), 2)
    #ranking clasificacion mensual fija del mes seleccionado (df_apuestas no se gasta)
    df_apuestas_select, _ = obtener_apuestas()
    df_ranking = df_apuestas_select.copy()
    df_ranking['desvio'] = df_ranking['apuesta'] - media_omie 
    df_ranking['desvio_%'] = abs(df_ranking['desvio'] / media_omie) * 100
    df_ranking['posicion'] = df_ranking['desvio_%'].rank(method = 'first', ascending = True).astype(int)
    df_ranking = df_ranking.drop(columns = 'mes_apuesta')
    df_ranking_powerrange = df_ranking.copy()
    df_ranking = df_ranking.sort_values(by ='posicion', ascending = True)

    print('df_ranking')
    print(df_ranking)

    #buscamos la posición 1 y la resaltamos
    def resaltar_podio(row):
        if row['posicion'] == 1:
            return ['background-color: darkgreen' for _ in row]
        elif row['posicion'] == 2:
            return ['background-color: forestgreen' for _ in row]
        elif row['posicion'] == 3:
            return ['background-color: seagreen' for _ in row]
        else:
            return ['' for _ in row]
    
    #buscamos la posicion del usuario y la resaltamos
    def resaltar_usuario(row, posicion):
        color='background-color: orange'
        return [color if row['posicion']==posicion else '' for _ in row]
    
    #buscamos la posición de OMIP y la resaltamos
    def resaltar_omip(row, posicion):
        color='background-color: blue'
        return [color if row['posicion']==posicion else '' for _ in row]
    
    posicion_omip = df_ranking.loc[df_ranking['nombre'] == 'OMIP', 'posicion'].values[0]
    
    #localizamos la posicion del usuario
    if st.session_state.nombre!='Invitad@':
        try:
            posicion_usuario = df_ranking.loc[df_ranking['nombre'] == st.session_state.nombre, 'posicion'].values[0]
            #aplicamos estilo
            df_ranking_styled=(
                df_ranking.style
                .apply(resaltar_podio, axis=1)
                .apply(lambda row: resaltar_usuario(row,posicion_usuario), axis=1)
                .apply(lambda row: resaltar_omip(row, posicion_omip), axis=1)
            )
        except IndexError:
            # Guardamos el mensaje de error en session_state
            st.session_state.error_message = f"No se encontró al usuario {st.session_state.nombre} en el ranking."
            df_ranking_styled = (
                df_ranking.style
                .apply(resaltar_podio, axis=1)
                .apply(lambda row: resaltar_omip(row, posicion_omip), axis=1)
            )
    else:
        df_ranking_styled=(
            df_ranking.style
            .apply(resaltar_podio, axis=1)
            .apply(lambda row: resaltar_omip(row, posicion_omip), axis=1)
        )



    df_ranking_styled=df_ranking_styled.format({
        'apuesta':'{:.2f}',
        'desvio':'{:.2f}',
        'desvio_%':'{:.2f}',
    })

    #usado para el omie evol, donde aparece el virtual según el día
    virtual = df_ranking.loc[df_ranking['posicion'] == 1, 'nombre'].iloc[0]
    
    

    
    fecha_ini_entrega=df_omie_mes_apuesta['datetime'].min()
    #código para obtener el último dia del mes a partir de la fecha primer dia
    fecha_fin_entrega=(fecha_ini_entrega + pd.DateOffset(months = 1) - pd.DateOffset(days = 1)).date()
    #creamos un df con los dias del mes de entrega
    df_rango_mes = pd.DataFrame({'datetime': pd.date_range(start=fecha_ini_entrega, end=fecha_fin_entrega)})
    df_rango_mes['dia']=df_rango_mes['datetime'].dt.day
    #df_omie_total_mes_select=df_rango_mes.merge(df_omie_mes_apuesta_select, on=['datetime','dia'], how='left')
    #ESTE DF ES EL QUE USAMOS PARA OBTENER EL LISTADO MVP VIRTUAL POR DIA
    df_omie_total_mes=df_rango_mes.merge(df_omie_mes_apuesta, on=['datetime','dia'], how='left')
    

    #return df_ranking, df_ranking_styled, df_ranking_select, df_omie_total_mes, df_omie_total_mes_select, media_omie_select, virtual, virtual_select, df_ranking_powerrange
    return df_ranking, df_ranking_styled, virtual, df_ranking_powerrange, df_omie_total_mes, media_omie


#FUNCION QUE NOS DEVUELVE VARIOS DFs----------------------------------------------------------------------------------
#un df con los virtual mpvstarpowers del mes (por dia)
#3 dfs con bloques de 10 (u 11) filas de los virtual mpv para visualizar en streamlit
def virtual(df_omie_total_mes, df_ranking_dia):    
    
    ultimo_dia_mes = df_omie_total_mes['dia'].max()
    
    df_virtual=pd.DataFrame(columns = ['dia','virtual_MVP','omie_media'])
    dias_por_bloque = 10
    #buscamos el último valor de omie disponible para luego obtener el dia
    ultimo_valor_omie=df_omie_total_mes['omie'].last_valid_index()
    ultimo_registro_dia=df_omie_total_mes.loc[ultimo_valor_omie, 'dia']
    
    df_apuestas_select, _ = obtener_apuestas()
    df_ranking_dia = df_apuestas_select.copy()
    df_ranking_dia = df_ranking_dia.drop(columns = 'mes_apuesta')
    for dia in range(1, ultimo_dia_mes + 1):
        
        #df_omie_hasta=df_omie_mes_apuesta[df_omie_mes_apuesta['dia']<=dia]
        df_omie_hasta = df_omie_total_mes[df_omie_total_mes['dia'] <= dia]
        media_omie = round(df_omie_hasta['omie'].mean(), 2)

        
        df_ranking_dia['desvio']=df_ranking_dia['apuesta']-media_omie
        df_ranking_dia['desvio_%']=abs(df_ranking_dia['desvio']/media_omie)*100
        df_ranking_dia['posicion']=df_ranking_dia['desvio_%'].rank(method='first', ascending=True).astype(int)
        
        if dia <= ultimo_registro_dia:
            ganador_virtual=df_ranking_dia.loc[df_ranking_dia['posicion']==1,'nombre'].iloc[0]
        else:
            ganador_virtual=''
        

        df_virtual=pd.concat([df_virtual, pd.DataFrame({'dia':[dia],'virtual_MVP':[ganador_virtual],'omie_media':[media_omie]})],ignore_index=True)
        df_virtual.reset_index(drop=True, inplace=True)
    
    if ultimo_dia_mes >= 31:
        # Bloque 1 (hasta el día 11)
        df_bloque_1 = df_virtual.iloc[:11].reset_index(drop=True)
        start_bloque_2 = 11
    else:
        # Bloque 1 (10 días)
        df_bloque_1 = df_virtual.iloc[:10].reset_index(drop=True)
        start_bloque_2 = 10

    # Bloque 2 (siguiente grupo de 10 días)
    end_bloque_2 = start_bloque_2 + dias_por_bloque
    df_bloque_2 = df_virtual.iloc[start_bloque_2:end_bloque_2].reset_index(drop=True)

    # Bloque 3 (siguiente grupo de 10 días o hasta el último registro)
    df_bloque_3 = df_virtual.iloc[end_bloque_2:].reset_index(drop=True)
    
    return df_virtual, df_bloque_1, df_bloque_2, df_bloque_3, ultimo_dia_mes



#GRÁFICO DE LA EVOLUCIÓN DE OMIE DURANTE EL MES DE LA APUESTA----------------------------------------------------------------------------------------------
#Incluye OMIE diario
#Incluye media OMIE
#Incluye media OMIP last3 mes anterior (el usado para los desvíos de la superporra)
#Incluye la apuesta del usuario

def omie_mes_apuesta(df_omie_total_mes_select, media_omie, omie_max):
    # a partir de aquí añadimos la escala y colores
    datos_limites = {
        'rango': [-10, 20.01, 40.01, 60.01, 80.01, 100.01, 120.01, 140.01, 10000], #9 elementos
        'valor_asignado': ['muy bajo', 'bajo', 'medio', 'alto', 'muy alto', 'chungo', 'xtrem', 'defcon3', 'defcon2'],
    }
    df_limites=pd.DataFrame(datos_limites)
    etiquetas = df_limites['valor_asignado'][:-1]
    df_omie_total_mes_select['escala']=pd.cut(df_omie_total_mes_select['omie'],bins=df_limites['rango'],labels=etiquetas,right=False)
    df_omie_total_mes_select['escala'] = df_omie_total_mes_select['escala'].cat.add_categories("Desconocido").fillna("Desconocido")
    #df_omie_total_mes_select['escala'] = df_omie_total_mes_select['escala'].fillna("Desconocido")
    colores = {
        'muy bajo': 'lightgreen',
        'bajo': 'green',
        #'medio': 'blue',
        'medio': '#24d4ff',
        #'alto': 'orange',
        'alto': '#004280',
        #'muy alto': 'red',
        'muy alto': 'orange',
        #'chungo': 'purple',
        'chungo': 'red',
        #'xtrem':'black',
        'xtrem':'darkred',
        'defcon3': 'purple',
        'defcon2': 'purple',
        'Desconocido' : 'gray'
    }
    colores = {
    'muy bajo': '#33cc33',  # Verde claro
    'bajo': '#009933',  # Verde más intenso
    'medio': '#2474A9',  # Azul verdoso intermedio
    'alto': '#002D72',  # Azul profundo
    'muy alto': '#7300A8',  # Púrpura azulado
    'chungo': '#990066',  # Magenta oscuro
    'xtrem': '#660033',  # Burdeos/morado oscuro
    'defcon3': '#4B0082',  # Índigo
    'defcon2': '#2E005C',  # Morado profundo
    'Desconocido': 'gray'  # Neutro
    }
    colores = {
    'muy bajo': '#2ECC71',  # Verde brillante (suave y visible)
    'bajo': '#1E8449',  # Verde más oscuro (natural y contrastado)
    'medio': '#2471A3',  # Azul verdoso (transición a tonos fríos)
    'alto': '#2C3E50',  # Azul profundo (más neutro y sobrio)
    'muy alto': '#6C3483',  # Púrpura índigo (equilibrado sin ser agresivo)
    'chungo': '#922B3E',  # Magenta-rojizo (intensidad pero sin ser estridente)
    'xtrem': '#5B2C6F',  # Púrpura oscuro (más dramático y fuerte)
    'defcon3': '#4A235A',  # Morado profundo
    'defcon2': '#2E005C',  # Morado oscuro extremo
    'Desconocido': 'gray'  # Neutralidad
    }
    colores = {
    'muy bajo': '#90EE90',  # Verde claro (fácil y suave a la vista)
    'bajo': '#2E8B57',  # Verde oscuro (tono natural)
    'medio': '#4682B4',  # Azul acero (transición a tonos fríos)
    'alto': '#1E3A5F',  # Azul profundo (sólido pero no agresivo)
    'muy alto': '#B565A7',  # Morado rosado (punto de transición)
    'chungo': '#D95F02',  # Naranja oscuro (advertencia sin ser agresivo)
    'xtrem': '#E6550D',  # Rojo anaranjado (peligro intermedio)
    'defcon3': '#A31E1E',  # Rojo fuerte (nivel crítico)
    'defcon2': '#800000',  # Rojo oscuro intenso (máximo riesgo)
    'Desconocido': 'gray'  # Neutralidad
    }
    colores = {
        'muy bajo': '#90EE90',  # Verde claro (fácil y suave a la vista)
        'bajo': '#2E8B57',  # Verde oscuro (tono natural)
        'medio': '#4682B4',  # Azul acero (transición a tonos fríos)
        'alto': '#1E3A5F',  # Azul profundo (sólido pero no agresivo)
        'muy alto': '#804674',  # Morado rosado (punto de transición)
        'chungo': '#B04E5A',  # Naranja oscuro (advertencia sin ser agresivo)
        'xtrem': '#A31E1E',  # Rojo anaranjado (peligro intermedio)
        'defcon3': 'darkred',  # Rojo fuerte (nivel crítico)
        'defcon2': '#800000',  # Rojo oscuro intenso (máximo riesgo)
        'Desconocido': 'gray'  # Neutralidad
        }
    
    ##E6550D # Rojo anaranjado (peligro intermedio)

    df_omie_total_mes_select['color']=df_omie_total_mes_select['escala'].map(colores)
    #print(df_omie_total_mes_select)
    valor_asignado_a_rango = {row['valor_asignado']: row['rango'] for _, row in df_limites.iterrows()}
    escala_dia=df_omie_total_mes_select['escala'].unique()
    escala_ordenada_dia = sorted(escala_dia, key=lambda x: valor_asignado_a_rango.get(x, float('inf')), reverse=True)


    df_omie_total_mes_select['escala']=pd.Categorical(
        df_omie_total_mes_select['escala'],
        categories=escala_ordenada_dia,
        ordered=True
        )

    # Gráfico de barras con los valores de OMIE diarios y aplicados los colores de la escala cavero vidal
    graf_omie=px.bar(df_omie_total_mes_select, x='dia', y = 'omie',
        color='escala',
        color_discrete_map=colores,
        category_orders={'escala':escala_ordenada_dia},
        #opacity=.7,
    )
    
    # Eliminamos la visualización de la legenda de colores de la escala cavero vidal
    graf_omie.update_traces(showlegend=False, selector=dict(type='bar'))

    # Gráfico de línea con la evolución de la media de omie
    graf_omie.add_trace(
        go.Scatter(
            x=df_omie_total_mes_select['dia'],
            #y=[media_omie]*len(df_omie_total_mes_select),
            y=df_omie_total_mes_select['omie_media'],
            #fill='tozeroy',
            mode='lines',
            #fillcolor='rgba(255, 100, 100, 0.5)',
            line=dict(color='yellow', width=2),
            name='OMIE - media evol',
        )
    )

    # Gráfico línea horizontal con la media mensual de OMIE en puntitos
    graf_omie.add_trace(
        go.Scatter(
            x=df_omie_total_mes_select['dia'],
            y=[media_omie]*len(df_omie_total_mes_select),
            #fill='tozeroy',
            mode='lines',
            #fillcolor='rgba(255, 100, 100, 0.5)',
            line=dict(dash='dot', color='yellow', width=2),
            name='OMIE - media mensual'
        )
    )
   
    # Gráfico línea horizontal de puntos con la media de OMIP last3 mes anterior
    graf_omie.add_trace(
        go.Scatter(
            x=df_omie_total_mes_select['dia'],
            y=[st.session_state.omip]*len(df_omie_total_mes_select), #['Precio'],
            #fill='tozeroy',
            mode='lines',
            #fillcolor='rgba(255, 100, 100, 0.5)',
            line=dict(dash='dot', color='sienna', width=3),
            name='OMIP - media last3 M-1'
        )
    )

    # Gráfico línea horizontal de puntos con la apuesta del usuario
    if st.session_state.nombre !='Invitad@':
        graf_omie.add_trace(
            go.Scatter(
                x=df_omie_total_mes_select['dia'],
                y=[st.session_state.apuesta_usuario]*len(df_omie_total_mes_select), #['Precio'],
                #fill='tozeroy',
                mode='lines',
                #fillcolor='rgba(255, 100, 100, 0.5)',
                line=dict(dash='dot', color='green', width=3),
                name='tu apuesta'
            )
        )

    dia_fin_mes=df_omie_total_mes_select['dia'].max()
    
    #modificaciones varias
    graf_omie.update_layout(
        #title=dict(
        #    text=f'Evolución de OMIE en {st.session_state.mes_miniporra_select}',
        #    x=.5,
        #    xanchor='center',
        #    ),
        yaxis_title='€/MWh',
        xaxis=dict(
            tickmode='linear',
            range=[.5,dia_fin_mes+.5],
            
            ),
        yaxis = dict(
            tick0=0,                      # Comenzar en 0
            dtick=20                      # Incrementos de 20
        ),    
        bargap = .2,
        legend=dict(
                orientation="h",  # Leyenda en horizontal
                yanchor='bottom',  # Alineación vertical en la parte inferior de la leyenda
                y=-.5,  # Colocarla ligeramente por encima del gráfico
                xanchor="center",  # Alineación horizontal centrada
                x=0.5,  # Posición horizontal centrada
                title_text=''
            )
    )

    
    #parametrizamos eje Y desde 0 hasta max OMIE diario + 10
    #graf_omie.update_yaxes(
    #range=[0,omie_max+20]
    #)

    return graf_omie





#-------------------------------------------------------------------------------------------------
def obtener_meff_mensual():
    
    #df_FTB = obtener_FTB()

    #filtramos por Periodo 'Mensual'
    df_FTB_mensual = st.session_state.df_historicos_FTB[st.session_state.df_historicos_FTB['Cod.'].str.startswith('FTBCM')]
    #hacemos copy del df
    df_FTB_mensual = df_FTB_mensual.copy()

    #RETURN: Lista con el mes-año tipo ene-24 obtenido de 'Entrega'
    li_mesaño=df_FTB_mensual['Entrega'].unique().tolist()
    #RETURN: Creamos un diccionario asociando el primer mes-año de la lista con 1 y así sucesivamente
    di_mesaño={mes: idx for idx, mes in enumerate(li_mesaño,start=1)}
    #print(di_mesaño)
    #creamos columna de número de meses desde el primer mes de entrega hasta el último
    df_FTB_mensual['Mes_Entrega']=df_FTB_mensual['Entrega'].map(di_mesaño)
    #esto es para que el nombre del mes corto sea en castellano
    locale.setlocale(locale.LC_TIME, 'es_ES')  # Para sistemas Windows
    # Crear una nueva columna 'mes_año' con el formato 'mes-abreviado-año-corto'
    df_FTB_mensual['Fecha'] = pd.to_datetime(df_FTB_mensual['Fecha'], errors='coerce')
    df_FTB_mensual['Fecha_corta'] = df_FTB_mensual['Fecha'].dt.strftime('%b-%y').str.replace(r'\.', '', regex=True)
    df_FTB_mensual['Precio']=pd.to_numeric(df_FTB_mensual['Precio'], errors='coerce')
    #RETURN: Creamos otra columna tipo mes indexado pero esta vez para el mes año de la fecha de los datos
    df_FTB_mensual['Mes_Fecha']=df_FTB_mensual['Fecha_corta'].map(di_mesaño)

    print('df_FTB_mensual')        
    print(df_FTB_mensual)
    
    #RETURN: Lista con 'Entrega' contiene '24', es decir, del año 2024  y 2025       
    li_entregas_2425 = df_FTB_mensual[df_FTB_mensual['Entrega'].str.contains(r'24|25|26', na=False)]['Entrega'].unique().tolist()
    
    return df_FTB_mensual, di_mesaño, li_entregas_2425, li_mesaño


def obtener_datos_mes_entrega(df_FTB_mensual, mes_entrega, entrega, df_omie_mensual):
    ## ESTE DATAFRAME LO USAMOS PARA OBTENER UNA GRÁFICA DE OMIP PARA EL MES DE ENTREGA (MINIPORRA) DESDE 6 MESES ATRÁS
    #mes_entrega viene en formato entero, como un índice que indica la posicón del mes de entrega seleccionado

    #filtramos hasta el mes anterior al de entrega
    df_FTB_mensual_entrega_menos1 = df_FTB_mensual[(df_FTB_mensual['Mes_Entrega']==mes_entrega) & (df_FTB_mensual['Mes_Fecha']<df_FTB_mensual['Mes_Entrega'])]
    #print(df_FTB_mensual_entrega_menos1)
    #filtramos hasta el mes de entrega incluido
    df_FTB_mensual_entrega = df_FTB_mensual[(df_FTB_mensual['Mes_Entrega']==mes_entrega) & (df_FTB_mensual['Mes_Fecha']<=df_FTB_mensual['Mes_Entrega'])]
    
    #dataframe con los 3 valores últimos para resaltarlos. USADOS PARA EL AREA DE LOS TRES ULTIMOS VALORES INCLUIDO EL MES DE ENTREGA
    df_FTB_mensual_entrega_last3=df_FTB_mensual_entrega.tail(3)
    #dataframe con los 3 valores últimos del mes anterior. USADOS PARA EL AREA DE LOS TRES ULTIMOS VALORES
    df_FTB_mensual_entrega_last3_menos1=df_FTB_mensual_entrega_menos1.tail(3)
    #media de omip
    omip_entrega=round(df_FTB_mensual_entrega_last3['Precio'].mean(),2)
    omip_entrega_menos1=round(df_FTB_mensual_entrega_last3_menos1['Precio'].mean(),2)

    #print('df_omie_mensual')
    #print(df_omie_mensual)

    #valor dinamico de omie para el mes de la miniporra (mes de entrega)
    df_omie_entrega=df_omie_mensual[df_omie_mensual['mes_apuesta']==entrega]['omie']

    #print('df_omie_entrega')
    #print(df_omie_entrega)


    if not df_omie_entrega.empty:
        omie_entrega=df_omie_entrega.iloc[0]
    else:
        omie_entrega=None
    
    
    #print(f'omie_entrega: {omie_entrega}')


    # PRIMER GRÁFICO DE DATOS. EVOLUCIÓN DE OMIP vs OMIE MEDIO
    # Gráfico de linea con la evolución de OMIP
    graf_futuros=px.line(df_FTB_mensual_entrega, x='Fecha',y='Precio',
        labels={'Precio':'€/MWh'},
    )
    # Le añadimos propiedades
    graf_futuros.update_traces(
        line=dict(color='sienna'),
        name='omip',
        showlegend=True
    )

    # Mostramos grid vertical
    graf_futuros.update_xaxes(
        showgrid=True
    )

    # Añadimos título y rangos de visualización
    graf_futuros.update_layout(
        #title=dict(
        #    text=f'Evolución de OMIP para el mes de {entrega}.',
        #    x=.5,
        #    xanchor='center',
        #),
        xaxis=dict(
            rangeslider=dict(
                visible=True,
                bgcolor='rgba(173, 216, 230, 0.5)'
            ),  
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(step="all")  # Visualizar todos los datos
                ]),
                #visible=True
            )
        ),
        legend=dict(
                orientation="h",  # Leyenda en horizontal
                yanchor='top',  # Alineación vertical en la parte inferior de la leyenda
                y=-.6,  # Colocarla ligeramente por encima del gráfico
                xanchor="center",  # Alineación horizontal centrada
                x=0.5,  # Posición horizontal centrada
                title_text=''
            )
    )
    
    # Añadimos rectángulo transparente con los tres precios últimos de OMIP incluido mes de entrega
    ancho=3
    graf_futuros.add_trace(
        go.Scatter(
            x=df_FTB_mensual_entrega_last3['Fecha'],
            y=[omip_entrega+ancho]*len(df_FTB_mensual_entrega_last3),
            mode='lines', 
            line=dict(color='rgba(255, 255, 204, 0.0)'),                   
            showlegend=False
        )
    )
    graf_futuros.add_trace(
        go.Scatter(
            x=df_FTB_mensual_entrega_last3['Fecha'],
            y=[omip_entrega-ancho]*len(df_FTB_mensual_entrega_last3), 
            fill='tonexty',
            mode='none',
            fillcolor='rgba(255, 255, 204, 0.2)',
            name='last 3',
            
        )
    )

    #añadimos rectangulo transparente con los tres precios últimos de OMIP
    graf_futuros.add_trace(
        go.Scatter(
            x=df_FTB_mensual_entrega_last3_menos1['Fecha'],
            y=[omip_entrega_menos1+ancho]*len(df_FTB_mensual_entrega_last3_menos1), 
            mode='lines',
            line=dict(color='rgba(255, 150, 150, 0.0)'),
            showlegend=False
            
        )
    )
    graf_futuros.add_trace(
        go.Scatter(
            x=df_FTB_mensual_entrega_last3_menos1['Fecha'],
            y=[omip_entrega_menos1-ancho]*len(df_FTB_mensual_entrega_last3_menos1), 
            fill='tonexty',
            mode='none',
            fillcolor='rgba(255, 150, 150, 0.2)',
            name='last3 M-1'
            
        )
    )
    
    # AÑADIMOS VALOR MEDIO DE OMIE PARA EL MES SELECCIONADO
    graf_futuros.add_trace(
        go.Scatter(
            x=df_FTB_mensual_entrega['Fecha'],
            y=[omie_entrega]*len(df_FTB_mensual_entrega), #['Precio'],
            #fill='tozeroy',
            mode='lines',
            fillcolor='rgba(255, 150, 150, 0.2)',
            line=dict(dash='dot', color='green'),
            name='omie media'
        )
    )

    # AÑADIMOS VALOR MEDIO DE OMIP MES EN CURSO PARA EL MES SELECCIONADO
    graf_futuros.add_trace(
        go.Scatter(
            x=df_FTB_mensual_entrega['Fecha'],
            #y=[omip_entrega]*len(df_FTB_mensual_entrega), 
            #x=df_FTB_mensual_entrega_last3_menos1['Fecha'],
            y=[omip_entrega_menos1]*len(df_FTB_mensual_entrega), 
            #fill='tozeroy',
            mode='lines',
            fillcolor='rgba(255, 150, 150, 0.2)',
            line=dict(dash='dot', color='sienna'),
            name='omip media mes anterior'
        )
    )
        
    return graf_futuros, omie_entrega, omip_entrega, omip_entrega_menos1, df_FTB_mensual_entrega


def omie_diario(df_omie_diario, entrega, omip_entrega):

    if df_omie_diario.empty:
        return None
    df_omie_diario_entrega = df_omie_diario[df_omie_diario['Entrega'] == entrega]
    #omie_entrega=round(df_omie_diario_entrega['omie'].mean(),2)
    fecha_ini_entrega = df_omie_diario_entrega['datetime'].min()
    #código para obtener el último dia del mes a partir de la fecha primer dia
    fecha_fin_entrega = (fecha_ini_entrega + pd.DateOffset(months = 1) - pd.DateOffset(days = 1)).date()
    #creamos un df con los dias del mes de entrega
    df_rango_dias_entrega = pd.DataFrame({'datetime': pd.date_range(start = fecha_ini_entrega, end = fecha_fin_entrega)})
    df_omie_diario_entrega_rango = df_rango_dias_entrega.merge(df_omie_diario_entrega, on = 'datetime', how = 'left')
    df_omie_diario_entrega_rango['omip'] = omip_entrega

    print ('df_omie_diario_entrega_rango')
    #print (df_omie_diario_entrega_rango)
    

    return df_omie_diario_entrega_rango

def obtener_datos_mes_anterior(df_FTB_mensual):
    #filtramos aquellos meses que sean justo uno menos que el mes de entrega
    #USAMOS EL DATAFRAME PARA OBTENER LOS ULTIMOS 3 VALORES DE CADA MES DE ENTREGA
    df_FTB_mensual_mes_anterior = df_FTB_mensual[df_FTB_mensual['Mes_Fecha'] == df_FTB_mensual['Mes_Entrega'] - 1]
    #de cada mes, nos quedamos sólo con los valores de las últimas tres sesiones
    df_FTB_mensual_mes_anterior_last3 = df_FTB_mensual_mes_anterior.groupby('Entrega').tail(3)
    #obtenemos la media de esos tres dias, por mes de entrega
    df_FTB_mensual_mes_anterior_last3 = df_FTB_mensual_mes_anterior_last3.groupby('Entrega', as_index=False)['Precio'].mean().round(2)
    ## ORDENAMOS CRONOLÓGICAMENTE POR MES DE ENTREGA TIPO ene-24, feb-24 ...
    #lista de meses
    months_order = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
    #convertimos 'Entrega' en categoría para poder ordenar
    df_FTB_mensual_mes_anterior_last3['Entrega'] = pd.Categorical(df_FTB_mensual_mes_anterior_last3['Entrega'], categories=[f'{m}-{y}' for y in ['23', '24', '25'] for m in months_order], ordered=True)
    #esta es la lista ordenada con los meses de entrega y la media de MEFF de los últimos tres dias
    df_FTB_mensual_mes_anterior_last3_ordered = df_FTB_mensual_mes_anterior_last3.sort_values('Entrega').reset_index(drop=True)
    print(df_FTB_mensual_mes_anterior_last3_ordered)
    return df_FTB_mensual_mes_anterior_last3_ordered



# Código para enviar mails de notificación a los usuarios++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def enviar_info(destinatario, nombre, mes, cuerpo, ultimo_dia_registro):
    
    remitente = "jovidal71@gmail.com"
    contrasena = st.secrets['PASSWORD_GMAIL']
    asunto = f'#minipoweromie {mes}'
    # Crear el mensaje
    mensaje = MIMEMultipart()
    mensaje['From'] = remitente
    mensaje['To'] = destinatario
    mensaje['Subject'] = asunto

    # Cuerpo del mensaje
    
    if cuerpo == 'cuerpo1':
        cuerpo_send = f"""\
        ¡Hola {nombre}!

        Ya está abierta la veda para que puedas registrar tu predicción en la #minipoweromie {mes}!!

        Accede con tu nick en:  
        🔗 https://spo-epowerapp.streamlit.app/

        ¡¡Gracias por tu participación y... Suerte!!

        NO ES NECESARIO RESPONDER A ESTE CORREO.  
        """
    elif cuerpo == 'cuerpo2':
        cuerpo_send = f"""\
        ¡Hola {nombre}!

        Recuerda que sigue abierto el plazo de registro de predicciones para la #minipoweromie {mes}!!

        Puedes modificarla tantas veces como quieras.

        Accede con tu nick en:  
        🔗 https://spo-epowerapp.streamlit.app/

        ¡¡Gracias por tu participación y... suerte!!

        NO ES NECESARIO RESPONDER A ESTE CORREO.  
        """
    else:
        cuerpo_send = f"""\
        ¡Hola {nombre}!

        Recuerda que hoy {ultimo_dia_registro} a las 23:59h se cierra el registro de predicciones para la #minipoweromie{mes}.

        Si ya tienes registrada la predicción, todavía puedes modificarla hasta esa hora.

        Accede con tu nick en:  
        🔗 https://spo-epowerapp.streamlit.app/

        ¡¡Gracias por tu participación y... suerte!!

        NO ES NECESARIO RESPONDER A ESTE CORREO.  
        """

    mensaje.attach(MIMEText(cuerpo_send, 'plain'))

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

#cambiar a True manualmente de momento para enviar emails
#flag_envio = True
flag_envio = False
mes = 'feb-26'
cuerpo = 'cuerpo3'
ultimo_dia_registro = 'viernes 30 de enero'

if flag_envio:
    spreadsheet_id_users = st.secrets['ID_DRIVE_USERS']
    worksheet, df_usuarios = acceder_google_sheets(spreadsheet_id_users)

    for _, fila in df_usuarios.iterrows():
        nombre=fila['nombre']
        email=fila['email']
        flag = enviar_info(email, nombre, mes, cuerpo, ultimo_dia_registro)

import streamlit as st
import pandas as pd
from apuestas import (
    omie_diario, obtener_omie_diario, 
    filtrar_mes_apuesta, resultados, omie_mes_apuesta, virtual, resultados_mensuales, obtener_clasificacion_porc, 
    grafico_clasificacion, obtener_comparativa, grafico_comparativo, obtener_omie_omip, grafico_omie_omip, obtener_apuestas,
    obtener_meff_mensual, obtener_datos_mes_entrega, obtener_datos_mes_anterior)
import time
from datetime import datetime
from utils.auth import acceder_google_sheets, autenticar_google_sheets
import base64

if "cache_cleared" not in st.session_state:
    st.cache_data.clear()  # Limpiar caché al iniciar
    st.session_state.cache_cleared = True  # Evita que se borre en cada interacción

if 'client' not in st.session_state: 
    st.session_state.client = autenticar_google_sheets()
    

def cargar_apuestas():
    spreadsheet_id_apuestas = st.secrets['ID_DRIVE_APUESTAS']
    st.session_state.worksheet_apuestas, st.session_state.df_apuestas = acceder_google_sheets(spreadsheet_id_apuestas)
    return

if 'worksheet_apuestas' not in st.session_state or 'df_apuestas' not in st.session_state:
    cargar_apuestas()

# Obtenemos los históricos de MEFF
if 'worksheet_meff' not in st.session_state or 'df_historicos_FTB' not in st.session_state:
    spreadsheet_id_meff = st.secrets['ID_DRIVE_MEFF']
    st.session_state.worksheet_meff, st.session_state.df_historicos_FTB = acceder_google_sheets(spreadsheet_id_meff)
    st.session_state.df_historicos_FTB['Fecha'] = pd.to_datetime(st.session_state.df_historicos_FTB['Fecha'], format = '%Y-%m-%d')
    st.session_state.ultimo_registro_meff = st.session_state.df_historicos_FTB['Fecha'].max().date()



def autoplay_audio(file_path: str):
                
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(
            md,
            unsafe_allow_html=True,
        )

# usado para las predicciones cuando se abre el plazo
def obtener_apuestas_mes(mes_apuesta):
    
    #df con las apuestas del mes_apuesta, usado para comprobar que no se repite ninguna 
    df_mes_apuesta = st.session_state.df_apuestas[st.session_state.df_apuestas['mes_apuesta'] == mes_apuesta]
    #df con todas las apuestas del usuario pero invertidas (la última es la primera), usado para visualización
    df_apuestas_user = st.session_state.df_apuestas[st.session_state.df_apuestas['nombre'] == st.session_state.nombre].iloc[::-1]
    #df usado para borrar en caso de actualizar la apuesta
    df_apuesta_user = st.session_state.df_apuestas[(st.session_state.df_apuestas['mes_apuesta'] == mes_apuesta) & (st.session_state.df_apuestas['nombre'] == st.session_state.nombre)]

    return df_apuesta_user, df_apuestas_user, df_mes_apuesta #, ws, df_apuestas

df_omie_diario, meses_miniporra = obtener_omie_diario()
meses_miniporra_invertidos = list(reversed(meses_miniporra))
#print(meses_miniporra_invertidos)
df_FTB_mensual, di_mesaño, li_entregas_2425, li_mesaño = obtener_meff_mensual()
valores_omip_last3 = obtener_datos_mes_anterior(df_FTB_mensual)
valores_omip = valores_omip_last3['Precio'].tolist()
valores_omip = valores_omip[:len(meses_miniporra)]
combo_omip = dict(zip(meses_miniporra, valores_omip))

print('combo omip')
print(combo_omip)

df_omip = pd.DataFrame({'mes_miniporra' : meses_miniporra,'omip' : valores_omip})


if 'mes_miniporra_select' not in st.session_state:
    st.session_state.mes_miniporra_select = meses_miniporra_invertidos[0]

print(f'Mes miniporra seleccionado: {st.session_state.mes_miniporra_select}')

st.session_state.omip = df_omip.loc[df_omip['mes_miniporra'] == st.session_state.mes_miniporra_select, 'omip'].values[0]
#print (st.session_state.omip)

ultimo_registro_omie, df_omie_mes_apuesta = filtrar_mes_apuesta(df_omie_diario)
#maximo de omie para definir max del ejeY del grafico de omie
omie_max = df_omie_mes_apuesta['omie'].max()

#establecer el último día con registros
if 'dia_seleccion' not in st.session_state:
    st.session_state.dia_seleccion=ultimo_registro_omie.day
if 'resetear' not in st.session_state:
    st.session_state.dia_seleccion=ultimo_registro_omie.day
#inicializamos animacion como false    
if 'animar' not in st.session_state:
    st.session_state.animar=False

#no se gasta de momento---------------------------------
def resetear():
    st.session_state.dia_seleccion=ultimo_registro_omie.day
def animar():
    st.session_state.dia_seleccion=1
    st.session_state.animar=True
    
if st.session_state.animar:
    for dia in range(1,11):
        st.session_state.dia_seleccion = dia
        #st.write(dia)
        
        time.sleep(1)
        st.rerun()    
    else:
        st.session_state.animar=False
#no se gasta de momento---------------------------------        

#pasamos los parámetros del df omie filtrado por el mes de la apuesta y el día seleccionado
#obtenemos el df del ranking del mes y el df de omie pero con todos los dias, para el gráfico omie-omip

#if 'meff' not in st.session_state:
#    st.session_state.meff=False

if "nombre" not in st.session_state:
    st.switch_page("spo.py")
    #st.stop()
else:
    try:
        df_ranking, df_ranking_styled, virtual_mvp, df_ranking_powerrange, df_omie_total_mes, media_omie = resultados(df_omie_mes_apuesta)
    except Exception as e:
        st.error('Error por inactividad. Logeate de nuevo')

num_participantes = len(df_ranking)
#media_omie=round(df_omie_total_mes['omie'].mean(),2)
df_virtual, df_bloque_1, df_bloque_2, df_bloque_3, dias_mes = virtual(df_omie_total_mes, df_ranking)

#dif_omie_omip=round(st.session_state.omip-media_omie_select,2)
#dif_omie_omip_porc=abs(round(dif_omie_omip*100/media_omie_select,2))




# LAYOUT DE LA PÁGINA-----------------------------------------------------------------------------------------------------------------------
st.title(f'Hola, :blue[{st.session_state.nombre}]!')
if 'error_message' in st.session_state:
    st.error(st.session_state.error_message)
    del st.session_state.error_message  # Limpiar mensaje

#st.warning('¡Plazo abierto para la **#minipower feb-25!** Accede a través de la pestaña "Predicciones" ',icon="⚠️")

tab1, tab2, tab3, tab4, tab5, tab6 =st.tabs(['MiniPowerOMIE', 'Power Range', 'SuperPowerOMIE', 'Estadísticas', 'OMIP', 'Predicciones'])


#CLASIFICACIÓN MENSUAL, GRÁFICO DE OMIE Y VIRTUALS DEL MES++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
with tab1:
    # Info general--------------------------------------------------
    st.info('En este apartado se encuentran datos generales del mes seleccionado, la clasificación mensual, la gráfica de los precios medios diarios de OMIE y los #Virtual del mes.',icon="ℹ️")
    with st.container():
        c1,c2,c3,c4,c5=st.columns(5)
        with c1:
            st.selectbox('Mes MiniPower', options = meses_miniporra_invertidos, key = 'mes_miniporra_select')
            #st.metric('Mes apuesta', value=mes_miniporra)
        with c3:
            st.metric('Día ultimo registro', value = ultimo_registro_omie.day)
        with c2:
            st.metric('Núm. participantes', value = num_participantes)    
        with c4:
            st.metric('Media OMIE', value = media_omie)
        with c5:
            if st.session_state.nombre=='Invitad@':
                st.session_state.apuesta_usuario = None
                st.metric('Tu predicción', value='--')
            else:
                try:
                    st.session_state.apuesta_usuario = df_ranking.loc[df_ranking['nombre'] == st.session_state.nombre, 'apuesta'].values[0]
                    st.metric('Tu predicción', value=f'{st.session_state.apuesta_usuario:.2f}')
                except (IndexError, KeyError):
                    st.session_state.apuesta_usuario = None
                    st.metric('Tu predicción', value='--')
            #st.metric('OMIP Last3 M-1', value=st.session_state.omip,delta=dif_omie_omip_porc)

    # Clasificacion minipower -----------------------------------------------------------
    st.subheader(f'Clasificación mensual de la minipower :orange[{st.session_state.mes_miniporra_select}]',divider='rainbow')
    st.markdown(
        f"""
        <p style='font-size:20px; color:gray; display:inline'>Virtual MVP StarPower: </p>
        &nbsp;
        <p style='font-size:36px; font-weight:bold; color:orange; display:inline'> {virtual_mvp}</p>
        """,
        unsafe_allow_html=True
    )
    st.dataframe(df_ranking_styled, hide_index=True, use_container_width=True)

    # Gráfico OMIE Evol--------------------------------------------
    st.subheader(f'OMIE Evolution de la minipower :orange[{st.session_state.mes_miniporra_select}]',divider='rainbow')
    graf_omie = omie_mes_apuesta(df_omie_total_mes, media_omie, omie_max)
    st.plotly_chart(graf_omie, key = 'graf1')

    #VIRTUAL MVPSTARPOWERS DEL MES------------------------------------------------------------------
    st.subheader('Listado de VirtualMVPStarPowers del mes',divider='rainbow')
    c1, c2, c3 = st.columns(3)
    #altura_1 = 425 if dias_mes == 31 else None
    altura_1 = 425 if dias_mes == 31 else 400
    with c1:
        st.dataframe(df_bloque_1, hide_index=True, use_container_width=True, height = altura_1,
        #st.dataframe(df_bloque_1, hide_index=True, width='stretch', height = altura_1,
                    column_config={
                        'dia':st.column_config.Column(width=None),
                        'virtual_MVP':st.column_config.Column(width='medium'),
                    })
    with st.container():
        with c2:
            st.dataframe(df_bloque_2, hide_index=True,use_container_width=True,
                        column_config={
                            'dia':st.column_config.Column(width=None),
                            'virtual_MVP':st.column_config.Column(width='medium'), 
                        })
    with st.container():
        with c3:
            st.dataframe(df_bloque_3, hide_index=True,use_container_width=True,
                        column_config={
                            'dia':st.column_config.Column(width=None),
                            'virtual_MVP':st.column_config.Column(width='medium'), 
                        })
            

# LISTADO POWER RANGE+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
with tab2:
    st.subheader('Listado PowerRange', divider='rainbow')
    st.info('Aquí puedes encontrar la horquilla con valor inferior y superior de la media que debe darse de OMIE para los días restantes.',icon="ℹ️")
    with st.container():
            c1,c2,c3,c4=st.columns(4)
            with c1:
                #st.metric('Mes apuesta', value=mes_miniporra)
                st.metric('Mes apuesta', value=st.session_state.mes_miniporra_select)
            with c3:
                st.metric('Día ultimo registro', value=ultimo_registro_omie.day)
            with c2:
                st.metric('Núm. participantes', value=num_participantes)    
            with c4:
                st.metric('Media OMIE', value=media_omie)


    #calculamos la suma de OMIE en los dias transcurridos
    suma_pool=media_omie*ultimo_registro_omie.day
    dias_mes=len(df_virtual)
    dias_faltantes=dias_mes - ultimo_registro_omie.day


    df_powerrange=df_ranking_powerrange.drop(columns=['desvio','desvio_%'])         
    df_powerrange['dif_siguiente']=df_powerrange['apuesta']-df_powerrange['apuesta'].shift(-1)       
    df_powerrange['lim_inf']=round(df_powerrange['apuesta']-df_powerrange['dif_siguiente']/2,2)
    df_powerrange['lim_sup']=df_powerrange['lim_inf'].shift(1)
    df_powerrange['omie_sup']=round((dias_mes*df_powerrange['lim_sup']-suma_pool)/dias_faltantes,2)
    df_powerrange['omie_inf']=df_powerrange['omie_sup'].shift(-1)

    df_powerrange_styled=(
        df_powerrange.style
        .format({
            'apuesta':'{:.2f}',
            'lim_inf':'{:.2f}',
            'lim_sup':'{:.2f}',
            'omie_inf':'{:.2f}',
            'omie_sup':'{:.2f}',
        })
    )



    st.dataframe(df_powerrange_styled, hide_index=True,use_container_width=True,
                column_order=('posicion','nombre','apuesta','lim_inf','lim_sup','omie_inf','omie_sup')
                )



# CLASIFICACIÓN GENERAL Y BATES A OMIP++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
with tab3:

    
    st.info('**Explicación**\n\n' 
        'Aquí tenemos a los aspirantes al **:orange[MVPStarPower]** según el año seleccionado, ordenados de menor a mayor desvío medio en porcentaje.  '
        'Por defecto se eliminan hasta los dos peores resultados si se han realizado más de :orange[10] predicciones. \n\n'
        'Pero opcionalmente puedes visualizar una clasificación alternativa sólo para aquellos **:orange[StarPowers]** con todas las predicciones realizadas \n\n'
        'Verás cómo la cosa cambia sustancialmente. \n'
        , icon = "ℹ️")
    col1, col2 = st.columns(2)
    with col1:
        
        if 'doce_meses' not in st.session_state:
            st.session_state.doce_meses = False

        año_spo_selected = st.selectbox('Selecciona el año', options=['2025','2024'])
        #if año_spo_selected == '2024':
        st.toggle('Prueba con los 12 meses', key='doce_meses')
        #nos quedamos con las dos últimas cifras del año, rollo 24 ó 25
        sufijo_año_spo = str(año_spo_selected)[-2:]
    

    #df_omie_omip = obtener_omie_omip(df_omie_mensual, combo_omip)
    df_ranking_mensual, df_acum_porc, df_omie_mensual_total, df_omie_mensual, df_ranking_mensual_podio, df_ranking_mensual, df_payoffs = resultados_mensuales(df_omie_diario, sufijo_año_spo, combo_omip)

    
    df_porra_desvios_porc, lista_starpowers, num_starpowers, ultimo_mes_porra, num_meses_porra = obtener_clasificacion_porc(df_acum_porc, sufijo_año_spo)
    graf_clasificacion = grafico_clasificacion(df_porra_desvios_porc)

    st.metric('Num. StarPowers', num_starpowers)
    st.plotly_chart(graf_clasificacion, use_container_width=True)

    st.subheader("Y tú, ¿bates a OMIP?",divider='rainbow')
    st.info(f'**:orange[Superpower]**: Selecciona tu **:orange[nombre]** y sabrás si bates a OMIP en la lucha por el **:orange[MVPStarPower20{sufijo_año_spo}]**. Recuerda que se han eliminado tus dos peores resultados si procede. Con OMIP se ha hecho exactamente lo mismo. La lista está ordenada alfabéticamente.',icon="ℹ️")
    lista_starpowers_ordenada=sorted(lista_starpowers)
    lista_starpowers_ordenada.insert(0,'')

    nombre_seleccionado=st.selectbox('Búscate',options=lista_starpowers_ordenada)
    #st.toggle('Prueba con los 12 meses')
    
    df_omie_omip = obtener_omie_omip(df_omie_mensual, combo_omip)
    graf_omie_omip = grafico_omie_omip(df_omie_omip)

    df_comp_nombre_omip_melted, media_jugador, media_omip = obtener_comparativa(nombre_seleccionado, df_porra_desvios_porc, df_omie_omip, num_meses_porra, ultimo_mes_porra, sufijo_año_spo)
    if nombre_seleccionado != '':
        
        dif_jugador_omip=round(media_jugador - media_omip, 1)
        
        if dif_jugador_omip < 0: #gana jugador

            if 'nombre_seleccionado_anterior' not in st.session_state:
                st.session_state.nombre_seleccionado_anterior=None
            if st.session_state.nombre_seleccionado_anterior !=nombre_seleccionado:
                #st.balloons()
                autoplay_audio("Niños.mp3")
                st.balloons()

                st.session_state.nombre_seleccionado_anterior= nombre_seleccionado

        col201,col202,col203=st.columns(3)
        with col201:
            st.metric('Media OMIP', value=f'{media_omip}%')
            
        with col202:
            st.metric('Media jugador',value=f'{media_jugador}%', delta=f'{dif_jugador_omip}%', delta_color='inverse')

    graf_comparativo = grafico_comparativo(df_comp_nombre_omip_melted, nombre_seleccionado)
    st.plotly_chart(graf_comparativo)

    st.subheader('SuperPowerOMIE: Más que un juego', divider = 'rainbow')
    st.info(('Mira el gráfico de abajo. Comparamos OMIE con OMIP en valores de desvío en €. '
             '**:red[Rojo]** significa que OMIP supera a OMIE y **:green[Verde]** al revés. '
             'Ahora imagina que hiciste cierres en base a OMIP...')
             , icon = "ℹ️")
    
    st.plotly_chart(graf_omie_omip)

    st.subheader('Tabla de payoffs', divider = 'rainbow')
    st.info(('Mira la tabla de abajo. Aquí tienes tus ganancias o pérdidas en función de tus coberturas OMIP. '
             '**:red[Rojo]** significa pérdidas y **:green[Verde]** son ganancias. '
             'En euros.')
             , icon = "ℹ️")
    
    st.dataframe(df_payoffs)

# ESTADÍSTICAS-------------------------------------------------------------------------------
with tab4:
    st.info('En este apartado encontrarás los podios ganadores de cada **:orange[Mini Power OMIE]**',icon="ℹ️")

    iconos = {1: "🏆", 2: "🥈", 3: "🥉"}
    df_ranking_mensual_podio = df_ranking_mensual_podio.rename(columns={pos: f"{iconos[pos]} {pos}°" for pos in [1, 2, 3]})

    def resaltar_nombre(nombre):
        color = 'background-color:yellow' if nombre == st.session_state.nombre else ''
        return color

    df_podios_24 = df_ranking_mensual_podio[df_ranking_mensual_podio['mes_apuesta'].str.contains('24')]
    df_podios_24 = df_podios_24.style.applymap(resaltar_nombre, subset=[f"{iconos[1]} 1°", f"{iconos[2]} 2°", f"{iconos[3]} 3°"])

    df_podios_25 = df_ranking_mensual_podio[df_ranking_mensual_podio['mes_apuesta'].str.contains('25')]
    df_podios_25 = df_podios_25.style.applymap(resaltar_nombre, subset=[f"{iconos[1]} 1°", f"{iconos[2]} 2°", f"{iconos[3]} 3°"])

    st.subheader('Podios de la SUPER POWER OMIE 2025')
    st.dataframe(df_podios_25, use_container_width=True, hide_index=True, height=470)
    st.subheader('Podios de la SUPER POWER OMIE 2024')
    st.dataframe(df_podios_24, use_container_width=True, hide_index=True, height=470)

    if st.session_state.nombre != 'Invitad@':
        st.subheader('Tus posiciones de cada MINI POWER OMIE')
        st.info('En este apartado encontrarás tus resultados en cada **:orange[MinipowerOMIE]**',icon="ℹ️")
        #st.dataframe(df_ranking_mensual, hide_index=True, use_container_width=True, height=520)
        st.data_editor(df_ranking_mensual, hide_index=True, use_container_width=True, height=525,
                       column_config={
                           'apuesta' : st.column_config.NumberColumn(format = '%.2f'),
                           'omie' : st.column_config.NumberColumn(format = '%.2f'),
                           'desvio' : st.column_config.NumberColumn(format = '%.2f'),
                           'desvio_%' : st.column_config.NumberColumn(format = '%.2f'),
                       }
                       )






# OMIP ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

with tab5:

    hoy  =datetime.now().date()
    mes_hoy = hoy.month
    año_hoy = hoy.year

    #st.session_state.df_historicos_FTB, ultimo_registro = obtener_historicos()
    #df_FTB = obtener_FTB(st.session_state.ultimo_registro)

    ##df_FTB_mensual, di_mesaño, li_entregas_2425, li_mesaño = obtener_meff_mensual(df_FTB)
    
    print(li_entregas_2425)
    index_mes_porra = di_mesaño.get(st.session_state.mes_miniporra_select, 0) - 2

    st.info('En este apartado encontrarás información sobre OMIP y su evolución',icon="ℹ️")
    # seleccion del mes a visualiar la evolución de OMIP
    entrega_seleccion = st.selectbox('Selecciona el mes a visualizar', options = li_entregas_2425, index = index_mes_porra)
    
    print(f'Mes entrega seleccionado para gráfico OMIP: {entrega_seleccion}')

    num_mes_entrega_seleccion = di_mesaño[entrega_seleccion]
    #st.write(df_omie_mensual)
    graf_futuros, omie_entrega, omip_entrega, omip_entrega_menos1, df_FTB_mensual_entrega = obtener_datos_mes_entrega(df_FTB_mensual, num_mes_entrega_seleccion, entrega_seleccion, df_omie_mensual_total)

    #df_omie_diario = obtener_omie_diario()
    #st.write(df_omie_diario)

    if omie_entrega != None:
        df_omie_diario_entrega_rango = omie_diario(df_omie_diario, entrega_seleccion, omip_entrega_menos1)
        #st.write(df_omie_diario_entrega_rango)
    
    st.subheader(f'OMIP vs OMIE en **:orange[{entrega_seleccion}]**', divider = 'rainbow')
    st.caption(f'Fecha último registro OMIP disponible: :blue[{st.session_state.ultimo_registro_meff.strftime("%d.%m.%Y")}]')
    #primera fila de indicadores
    col101,col102,col103=st.columns(3)
    with col101:
        st.metric('OMIE media', value = omie_entrega)
    with col102:
        st.metric('OMIP (mes anterior)',value=omip_entrega_menos1, help='Valor medio de OMIP de los últimos tres dias del mes anterior. Valor estático y usado en la sección ¿Bates a OMIP?.')
    with col103:
        if omie_entrega!=None:
            dif_omipm1_omie=round(omip_entrega_menos1-omie_entrega,2)
            delta_dif_m1=round((dif_omipm1_omie/omie_entrega)*100,2)
            st.metric('Diferencia', value=dif_omipm1_omie,delta=f'{delta_dif_m1}%')

    # Segunda fila de indicadores
    col111,col112,col113=st.columns(3)
    #with col111:
        #actualizar_meff = st.button('Actualizar MEFF', use_container_width=True)
        #if actualizar_meff:
        #    st.session_state.meff=True
            #obtener_FTB.clear()
            #st.rerun()
    with col112:
        st.metric('OMIP (mes en curso)',value=omip_entrega, help='Valor medio de OMIP de los tres últimos días disponibles durante el mes en curso. Es un valor dinámico.')
    with col113:
        if omie_entrega!=None:
            dif_omip_omie=round(omip_entrega-omie_entrega,2)
            delta_dif=round((dif_omip_omie/omie_entrega)*100,2)
            st.metric('Diferencia', value=dif_omip_omie,delta=f'{delta_dif}%')

    st.subheader(f'Evolución de OMIP para el mes de **:orange[{entrega_seleccion}]**', divider = 'rainbow')
    st.write (graf_futuros)

    #st.session_state.meff


# APUESTAS --------------------------------------------------------------------------------------------------------------------------------
#provisional
#mes_apuesta = None
mes_apuesta = 'feb-26'


with tab6:

    
    
    infogen_apuesta=st.empty()
    infoper_apuesta=st.empty()
    infoper1_apuesta=st.empty()        
    intro_apuesta=st.empty()

    # info general sobre el estado de la apertura o cierre
    if mes_apuesta is None:
        infogen_apuesta.info('Plazo cerrado.')
        if st.session_state.nombre=='Invitad@':
            infoper_apuesta.error('¡Regístrate para poder realizar predicciones!')
    else:
        infogen_apuesta.info(f'¡Plazo abierto para la minipoweromie {mes_apuesta}!')
    

        if st.session_state.nombre=='Invitad@':
            infoper_apuesta.error('¡Regístrate para poder realizar predicciones!')
        else:
            #ws, df_apuestas, df_apuestas_select = obtener_apuestas()
            #df con las apuestas del mes_apuesta, usado para comprobar que no se repite ninguna 
            #df_mes_apuesta=df_apuestas[df_apuestas['mes_apuesta']==mes_apuesta]
            #df con todas las apuestas del usuario pero invertidas (la última es la primera), usado para visualización
            #df_apuestas_user=df_apuestas[df_apuestas['nombre']==st.session_state.nombre].iloc[::-1]
            #df usado para borrar en caso de actualizar la apuesta
            #df_apuesta_user=df_apuestas[(df_apuestas['mes_apuesta']==mes_apuesta) & (df_apuestas['nombre']==st.session_state.nombre)]

            #df_apuesta_user, df_apuestas_user, df_mes_apuesta, ws, st.session_state.df_apuestas = obtener_apuestas_mes(mes_apuesta)
            df_apuesta_user, df_apuestas_user, df_mes_apuesta = obtener_apuestas_mes(mes_apuesta)
            # usamos el df del usuario
            # comprobamos primero si ya ha apostado para el mes_apuesta
            if mes_apuesta in df_apuestas_user['mes_apuesta'].values:
                infoper_apuesta.warning(f'Ya tienes la predicción realizada para {mes_apuesta}. Puedes modificarla hasta el cierre de las mismas.')
                infoper1_apuesta.dataframe(df_apuesta_user, hide_index=True, use_container_width=True,
                                column_config={
                                    'apuesta': st.column_config.NumberColumn(format = '%.2f')
                                    }
                                )
                #fila a borrar en el sheets de apuestas
                apuesta_borrar=int(df_apuesta_user.index[0] + 2)
            else:
                infoper_apuesta.warning(f'Todavía no tienes realizada la predicción para {mes_apuesta}. Puedes añadirla y modificarla hasta el cierre de las mismas.')
            
                
            form_apuesta=intro_apuesta.form('Formulario de introducción de predicciones')
            with form_apuesta:
                verif_apuesta=st.empty()
                apuesta=st.number_input(f'Introduce el valor de la predicción para la #minipower {mes_apuesta}', min_value=0.00, step=.01, format='%0.2f')
                # comprobamos segundo que no hay una apuesta igual para ese mes_apuesta
                
                

                boton_apostar=st.form_submit_button('Registrar o actualizar predicción', use_container_width=True, type='primary')
                if boton_apostar:
                        #df_apuestas, df_apuestas_select=obtener_apuestas()
                        if apuesta in df_mes_apuesta['apuesta'].values:
                            verif_apuesta.error('Valor de predicción ya realizado. Por favor, ingresa una nueva!')
                        else:
                            verif_apuesta.success('Predicción válida. Registrando...')
                            if not df_apuesta_user.empty:
                                #ws.delete_rows(apuesta_borrar)
                                st.session_state.worksheet_apuestas.delete_rows(apuesta_borrar)
                            ahora=datetime.now()
                            fecha_registro=ahora.strftime('%Y-%m-%d %H:%M:%S')
                            # accedemos al sheets de apuestas
                            
                            #spreadsheet_id_apuestas = '1y3Zd6phwut0yDKX8rB_t7xvJ6J3pLV95P6VQxvl3fu8'
                            #worksheet_apuestas, df_apuestas = acceder_google_sheets(spreadsheet_id_apuestas)

                            nuevo_apuesta=[mes_apuesta, st.session_state.nombre, f'{apuesta:.2f}', fecha_registro,]
                            #ws.append_row(nuevo_apuesta)
                            st.session_state.worksheet_apuestas.append_row(nuevo_apuesta)
                            
                            #worksheet_apuestas.append_row(nuevo_apuesta)
                            cargar_apuestas()

                            #comprobamos el registro de la apuesta
                            #worksheet_apuestas, df_apuestas = acceder_google_sheets(spreadsheet_id_apuestas)
                            #df_apuesta_user, df_apuestas_user, df_mes_apuesta, ws, df_apuestas = obtener_apuestas_mes(mes_apuesta)
                            df_apuesta_user, df_apuestas_user, df_mes_apuesta = obtener_apuestas_mes(mes_apuesta)
                            #df_apuestas_user=df_apuestas[df_apuestas['nombre']==st.session_state.nombre].iloc[::-1]
                            infoper_apuesta.warning(f'Ya tienes la predicción realizada para {mes_apuesta}. Puedes modificarla hasta el cierre de las mismas.')
                            infoper1_apuesta.dataframe(df_apuesta_user, hide_index=True, use_container_width=True,
                                column_config={
                                    'apuesta': st.column_config.NumberColumn(format = '%.2f')
                                    }
                                )
                            verif_apuesta.success('Predicción verificada!')
                            #st.dataframe(df_apuestas_user, hide_index=True, use_container_width=True,
                            #    column_config={
                            #        'apuesta': st.column_config.NumberColumn(format = '%.2f')
                            #        }
                            #    )
    
    





if st.button('Salir'):
    st.session_state.nombre = None
    st.switch_page('spo.py')


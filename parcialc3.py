import psycopg2
import streamlit as st
import pandas as pd
import subprocess
import os

## David Penilla - 69675

st.set_page_config(page_title='Parcial Corte 3: postgreSQL')


def init_connection():
    return psycopg2.connect(**st.secrets["db_credentials"])


def exec_query(query, mod=True):
    conn = init_connection()
    with conn.cursor() as c:
        c.execute(query)
        conn.commit()
        if mod:
            res = c.fetchall()
        conn.close()
        return res if mod else None


st.title('Parcial Corte 3: postgreSQL')
st.subheader('''----------------------------------------------------------------\n
reconsidere mi nota profe porfavor...''')



clase_trig, paliza_trig, partida_trig = st.columns(3)
st.text('Triggers implementados: ')
with clase_trig:
    with st.expander('Cambio Rol Jugador',True):
        st.markdown('''
        create or replace function change_rol()
        returns trigger
        language PLPGSQL as
        $$
        begin

            if (new.clase != old.clase ) then

                update jugadores 
                set roles = array_append(roles,old.clase)
                where id = new.id;
            end if; 

            return new;
        end;
        $$

        create trigger cambiar_rol
        after update on jugadores
        for each row execute procedure change_rol();
        ''')

with paliza_trig:
    with st.expander('Una partida desigual', True):
        st.markdown('''
        CREATE or REPLACE FUNCTION public.que_paliza() RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        begin 

        if (new.puntajes[1] > 9 and new.puntajes[2] < 2) then 
            insert into palizas_historicas 
            values ( new.puntajes[1],now(), new.puntajes[2],
            cast( array[new.equipo_a,new.equipo_b] as t_equipo[] ),
            new.id,new.equipo_a); 
        elsif ( new.puntajes[2] > 9 and new.puntajes[1] < 2 ) then 
             insert into palizas_historicas(asesinatos_A,fecha,asesinatos_B,equipos,id,ganador) 
            values ( new.puntajes[1],now(), new.puntajes[2],
            cast( array[new.equipo_a,new.equipo_b] as t_equipo[] ),
            new.id,new.equipo_b); 

        end if;

        return new;
        end;
        $$; 


        create trigger conmemorar_paliza
        after insert or update
        on partida
        for each row execute function que_paliza();
        ''')

with partida_trig:
    with st.expander('Creacion Partida: Vinculo Equipos', True):
        st.markdown('''
        ```plsql
        CREATE FUNCTION public.new_partida() RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        begin
	
	        insert into equipos(players)
	        values (new.equipo_a),(new.equipo_b);
	
	        new.id_equipo_a = (select id from equipos where players = new.equipo_a);	
	        new.id_equipo_b = (select id from equipos where players = new.equipo_b);

	    return new;
        end;
        ```

        ''')



st.subheader('1. Consultas')
a,b,c,d,e = st.row(5)

query_a = exec_query('''

select * from jugadores
where 'utilidad'=all(roles)
or clase='utilidad'
order by puntuacion
''')

query_b = exec_query('''

select nombre into temp no_defensores from jugadores 
where clase <> 'defensor';

select * from partida 
where
   player1(equipo_a) in (select * from no_defensores)
and player2(equipo_a) in (select * from no_defensores)
and player3(equipo_a) in (select * from no_defensores)
and player1(equipo_b) in (select * from no_defensores)
and player2(equipo_b) in (select * from no_defensores)
and player3(equipo_b) in (select * from no_defensores);
''')

query_c = exec_query('''

select * from jugadores 
where clase = (select clase from jugadores where nombre = 'Mario')
or cast (clase as character varying) = 
any(cast 
    ((select roles from jugadores where nombre = 'Mario') 
    as character varying[]));
''')

query_d = exec_query('''

select * from atacante inner join jugadores on atacante.id = jugadores.id
where tipo_arma = 'rango largo' order by puntuacion;
''')

query_e = exec_query('''

select * from jugadores where puntuacion = 
(select max(puntuacion) from jugadores);
''')


with a:
    st.dataframe(pd.DataFrame(query_a,
    columns = {'nombre','correo','premium','clase','id','puntuacion','roles'}))

with b:
    st.dataframe(pd.DataFrame(query_b,
    columns = {'equipo_a','equipo_b','id','puntajes','id_equipo_a','id_equipo_b'}))

with c:
    st.dataframe(pd.DataFrame(query_c,
    columns = {'nombre','correo','premium','clase','id','puntuacion','roles'}))

with d:
    st.dataframe(pd.DataFrame(query_d,
    columns = {'tipo_arma','damage','poder_especial','nombre','correo','premium','clase','id','puntuacion','roles'}))

with e:
    st.dataframe(pd.DataFrame(query_e),
    columns = {'nombre','correo','premium','clase','id','puntuacion','roles'})


    

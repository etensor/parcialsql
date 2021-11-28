from attr import s
from numpy import e
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
st.subheader('''\n
reconsidere mi nota profe porfavor...\n en sus manos está mi materia.\n - David Penilla ''')



st.subheader('1. Consultas')
a = st.container()
b = st.container()
c = st.container()
d = st.container()
e = st.container()

sql_a = r'''

select * from jugadores
where 'utilidad'=all(roles)
or clase='utilidad'
order by puntuacion
'''

sql_b = r'''

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
'''

sql_c = r'''

select * from jugadores 
where clase = (select clase from jugadores where nombre = 'Mario')
or cast (clase as character varying) = 
any(cast 
    ((select roles from jugadores where nombre = 'Mario') 
    as character varying[]));
'''

sql_d = r'''

select * from atacante inner join jugadores on atacante.id = jugadores.id
where tipo_arma = 'rango largo' order by puntuacion;
'''

sql_e = r'''

select * from jugadores where puntuacion = 
(select max(puntuacion) from jugadores);
'''

query_a = exec_query(sql_a)
query_b = exec_query(sql_b)
query_c = exec_query(sql_c)
query_d = exec_query(sql_d)
query_e = exec_query(sql_e)

with a:
    with st.expander('1. ¿Qué jugadores juegan más de utilidad?',True):
        st.code(sql_a,language='sql')
        st.dataframe(pd.DataFrame(query_a,
        columns = {'nombre','correo','premium','clase','id','puntuacion','roles'}))


with b:
    with st.expander('2. Qué partidas tienen jugadores que no juega de defensa',True):
        st.code(sql_b, language='sql')
        st.dataframe(pd.DataFrame(query_b,
        columns = {'equipo_a','equipo_b','id','puntajes','id_equipo_a','id_equipo_b'}))

with c:
    with st.expander('3. Qué jugadores juegan en todos los roles que juega el jugador Mario',True):
        st.code(sql_c, language='sql')
        st.dataframe(pd.DataFrame(query_c,
        columns = {'nombre','correo','premium','clase','id','puntuacion','roles'}))

with d:
    with st.expander('4. Qué jugadores juegan más con armas de largo alcance', True):
        st.code(sql_d, language='sql')
        st.dataframe(pd.DataFrame(query_d))
        #columns = {'tipo_arma','damage','poder_especial','id','nombre','correo','premium','clase','id','puntuacion','roles'}))

with e:
    with st.expander('5. ¿Qué jugadores tienen el puntaje del jugador que más puntos tiene actualmente en la base de datos? ', True):
        st.code(sql_e, language='sql')
        st.dataframe(pd.DataFrame(query_e,
        columns = {'nombre','correo','premium','clase','id','puntuacion','roles'}))

st.subheader('2. Triggers implementados: ')

clase_trig = st.container()
paliza_trig = st.container()
partida_trig = st.container()


with clase_trig:
    with st.expander('Cambio Rol Jugador', True):
        st.code('''
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
        ''', language='sql')

with paliza_trig:
    with st.expander('Una partida desigual', True):
        st.code('''
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
        ''', language='sql')

with partida_trig:
    with st.expander('Creacion Partida: Vinculo Equipos', True):
        st.code('''
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

        ''', language='sql')

with st.container():
    with st.expander(' Finalización Partida ', True):
        st.code('''
        CREATE FUNCTION public.end_partida() RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        declare
            winner t_equipo;
        begin

        if (new.puntajes[1] = 10) then
            winner := new.equipo_a;

            insert into public.registro
            values (new.puntajes[1],now(),new.puntajes[2],
                    cast (array[new.equipo_a,new.equipo_b] as t_equipo[]),
                    default, winner);

        elsif ( new.puntajes[2] = 10 ) then
            winner := new.equipo_b;

            insert into public.registro
            values (new.puntajes[1],now(),new.puntajes[2],
                    cast (array[new.equipo_a,new.equipo_b] as t_equipo[]),
                    default, winner);

        end if; 

        return new;
        end;
        $$;

        CREATE TRIGGER terminar_partida 
        AFTER INSERT OR UPDATE ON public.partida 
        FOR EACH ROW EXECUTE FUNCTION public.end_partida();
    '''
    ,language='sql')


st.subheader('3. Vistas')
st.write('''
Crear una vista que consista en los jugadores que nunca 
hayan jugado una partida, pero que esten registrados 
en la base de datos. ''')

st.code('''
create view no_han_jugado as
select * from jugadores where 
    nombre not in ( select player1(players) from equipos )
and nombre not in ( select player2(players) from equipos )
and nombre not in ( select player3(players) from equipos );

''',language='sql')


st.subheader('4. Indices')
st.write('''
Yo le aplicaria indices a la tabla jugadores ya que es la principal y van a estar
 constantemente en partidas. De esta forma se podría acelerar el sistema
 ya que se trabajaría con los jugadores más activos en la base de datos, que
 podria ser otra columna, horas de juego recientes.

Otra tabla probablemente extensa y abierta a optimizaciones sería la de partida, ya que puede que haya partidas más activas que otras.

Y si el registro es muy extenso (ya se jugaron muchas partidas), tambien valdría la pena

aplicar un indice ya que podría reorganizar el registro a partir de su fecha y así

volver más rápidas las consultas que la llamen.
''')


st.info('Muchas gracias por su atención.')

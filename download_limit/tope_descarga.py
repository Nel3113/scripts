from datetime import date
from datetime import datetime
from distutils.log import error
from logging import NullHandler
from multiprocessing import connection
from typing import final
import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorPrepared
import os

#data
host = "192.168.11.53"
user = "scripts"
password = "xxxxxxxxx"
db_coopvgg = "CoopVGG"
db_radius="radius"
db_freeradius="freeradius"
secret ="can't show"


#obtain day and month
fecha = date.today()
mes = fecha.strftime("%m")
año = fecha.strftime("%Y")
dia = fecha.day

log = open('/usr/local/bin/tope_log-'+str(fecha)+'.txt', 'w')
i = 0

def usage_radius(username):
    try:
        con_db_radius = mysql.connector.connect(user = user, password=password, host=host, database=db_radius )
        cursor2 = con_db_radius.cursor(MySQLCursorPrepared)
        print("Conexion exitosa\n")

        select2="SELECT SUM(acctoutputoctets)/1000/1000/1000 FROM radius.radacct_ro WHERE username=%s AND acctstarttime like '"+año+"-"+mes+"%';"
        cursor2.execute(select2, (username,))
        reg = cursor2.fetchone()
        usage_rad = reg[0]
        if usage_rad == None:
            usage_rad = 0
        
        
        cursor2.close()

    except mysql.connector.Error:
        print("Failed to retrieve data: ", error)
    finally:
        if (con_db_radius):
            con_db_radius.close()
            print("Connection closed\n")
    return usage_rad

def usage_freeradius(username):
    try:
        con_db_freeradius = mysql.connector.connect(user = user, password=password, host=host, database=db_freeradius )
        cursor3 = con_db_freeradius.cursor()
        print("Conexion exitosa\n")

        select4="SELECT SUM(acctoutputoctets)/1000/1000/1000 FROM radacct_radius_3 WHERE username=%s AND (AcctStopTime IS NULL OR AcctStopTime = '0000-00-00 00:00:00');"
        cursor3.execute(select4, (username,))
        reg = cursor3.fetchone()
        usage_freerad = reg[0]
        if usage_freerad == None:
            usage_freerad = 0
           
        cursor3.close()

    except mysql.connector.Error:
        print("Failed to retrieve data: ", error)
    finally:
        if (con_db_freeradius):
            con_db_freeradius.close()
            print("Connection closed\n")
    return usage_freerad  

def update(username, setear, contope, sintope):
    try:
        con_db_freeradius = mysql.connector.connect(user = user, password=password, host=host, database=db_freeradius )
        cursor3 = con_db_freeradius.cursor()

        select_perfil_real_activo="SELECT Value from radreply where username =%s AND (Value like '%down' or Value like '%down-tope');" 
        cursor3.execute(select_perfil_real_activo, (username,))
        download = cursor3.fetchone()
        
        if download == None:
            
            return
            
        else:    
            otro_perfil = download[0]
                    
        update="update radreply set Value = '"+setear+"' where username ='"+username+"' and (Value ='"+sintope+"' or Value ='"+contope+"' or Value ='"+otro_perfil+"');"
        cursor3.execute(update)
        log.write("UPDATE: "+update+"\n")
        con_db_freeradius.commit()

        selectNAS="SELECT username, nasipaddress FROM radacct_radius_3 WHERE username=%s AND (AcctStopTime IS NULL OR AcctStopTime = '0000-00-00 00:00:00') ORDER BY AcctStartTime DESC LIMIT 1;"
        cursor3.execute(selectNAS, (username,))
        conexion = cursor3.fetchone()
        if conexion != None:
            NAS = conexion[1]
            os.system("echo User-Name="+str(username)+" | radclient -x "+str(NAS)+":1700 disconnect "+secret)
            log.write("Desconecto a este usuario por el update "+str(fecha)+"\n")
            log.write("echo User-Name="+str(username)+" | radclient -x "+str(NAS)+":1700 disconnect "+secret+"\n")

        cursor3.close()

    except mysql.connector.Error:
        print("Failed to retrieve data: ", error)
    finally:
        if (con_db_freeradius):
            con_db_freeradius.close()
            print("Connection closed\n")

def averiguo_si_ya_venia_topeado(username):
     #to see if the user was already topped from the day before
    try:
        con_db_freeradius = mysql.connector.connect(user = user, password=password, host=host, database=db_freeradius )
        cursor3 = con_db_freeradius.cursor()
       
        selectValue="SELECT username from radreply where UserName=%s AND Value like '%down-tope';"
        cursor3.execute(selectValue, (username,))
        reg = cursor3.fetchone()
        if reg != None:
        
            estaba_topeado = "si"
        else:
            estaba_topeado = "no"

        cursor3.close()
        
    except mysql.connector.Error:
        print("Failed to retrieve data: ", error)
    finally:
        if (con_db_freeradius):
            con_db_freeradius.close()
            print("Connection closed\n")
        log.write("¿Tenia tope previo?: "+estaba_topeado+"\n")    
    return estaba_topeado


con_db_coopvgg = mysql.connector.connect(user = user, password=password, host=host, database=db_coopvgg )
cursor = con_db_coopvgg.cursor()
select1="SELECT * FROM radtope ORDER BY username;"

cursor.execute(select1)
usuarios = cursor.fetchall()

log.write("*************** COMIENZO **************\n")

for row in usuarios:
    i = i+1
    username = row[1]
    limite = int(row[2])/1000/1000/1000
    sintope = row[3]
    contope = row[4]

    log.write("CICLO PARA: "+username+"\n")

    if dia == 1:
        
        setear = sintope
        log.write("se va a setear: "+setear+"\n")
        update(username, setear, contope, sintope)
        continue
    else:

        a = usage_radius(username)
        b = usage_freeradius(username)
        total = a+b

        log.write('USO RADIUS: '+str(a)+' USO FREERADIUS '+str(b)+' CONSUMO TOTAL: '+str(total)+' LIMITE: '+str(limite)+'\n')
    
        if total >= limite:
            setear = contope
            log.write('Se va a setear el perfil: '+setear+'\n')

            tiene_tope = averiguo_si_ya_venia_topeado(username)

            if tiene_tope == "no":
                update(username, setear, contope, sintope)
                log.write("Se le puso el tope\n")

            continue
        else:
            log.write("Termina su ronda porque no llego al limite\n")
    continue
        
log.write('************************* FIN *******************************\n')
log.write('Iteraciones: '+str(i))

cursor.close()
con_db_coopvgg.close()

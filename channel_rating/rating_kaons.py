import requests, datetime, time, re, telnetlib, subprocess, paramiko, sqlite3, xml.etree.ElementTree as ET, concurrent.futures
from datetime import datetime
import id_canales 

# Datos STB Kaon
kaon_user = 'root'
kaon_pass = 'passxxxxx'
telnet_port = 23
command = "cat /tmp/flash/kaon_settings.ini | grep tuned_url"

# Datos STB Entone
entone_user = 'root'
entone_pass = 'passxxxxxx'
ssh_port = 10022
command_entone = 'cat /tmp/dbg/avstream/DECODER* | grep address: '

# Counters
stb_counter = 0
kaon_counter = 0
kaon_counter_reached = 0
entone_counter = 0
entone_counter_reached = 0

# Inicializo log
fecha = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
log = open(f'/var/log/rating/rating_{fecha}.txt', 'w')

def ping(ip):
    try:
        subprocess.check_output(['ping', '-c', '1', ip])
        return True
    except subprocess.CalledProcessError:
        return False

def api_call(api_command):
    response = requests.get(api_command)
    if response.status_code == 200:
        xml = response.text
        root = ET.fromstring(xml)
        return root
    else:
        print('La consulta a la API fallo')
        log.write('La consulta a la API fallo\n')
        exit()

def login():
    root = api_call('http://172.24.1.4:7780/dataservices/cdk?SP=md_adm.login_with_session(%27nguidabria%27,%27Nelson3113%27,%27ng%27,?int%20status)')   
    element = root.find('md_adm.login_with_session')
    status = element.get('status')
    if status == '0' or status == '-2':
        return True
    else:
        log.write(f"Codigo de error de la api: {status}\n")
        return False
      
def logoff():
    root = api_call('http://172.24.1.4:7780/dataservices/cdk?SP=md_adm.log_off(%27ng%27,?,?int%20status)')
    element = root.find('md_adm.log_off')
    status = element.get('status')
    if status == '0':
        print("Deslogueo exitoso de la api, bye")
        log.write("Deslogueo exitoso de la api, bye\n")     
    return False
   
def worker_kaon(ip_address):
    if ping(ip_address):                       
        try:
            tn = telnetlib.Telnet(ip_address, telnet_port, 1)
            res = str(tn.read_until(b"login: ", 1))
            if res != "b''":                             
                tn.write(kaon_user.encode('ascii') + b"\n")
                tn.read_until(b"Password: ")
                tn.write(kaon_pass.encode('ascii') + b"\n")
                tn.write(command.encode('ascii')+ b"\n")
                time.sleep(2)
                response = str(tn.read_very_eager())                                  
                tn.close()
                patron_ip = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
                ip_canal = re.findall(patron_ip, response)
            
                if ip_canal != []: 
                    ip_canal_var = ip_canal[0]
                    print(f"Canal sintonizado: {ip_canal_var}")                            
                    return ip_canal_var
            else:
                return False                                           
        except (EOFError, TimeoutError, ConnectionRefusedError, ConnectionResetError) as e:
            print(e)           
    else:
        print(f"deco: {ip_address} no respondio el ping")
        return False

def worker_entone(ip_address):
    if ping(ip_address):                       
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip_address, port=ssh_port, username=entone_user, password=entone_pass)
            stdin, stdout, stderr = client.exec_command(command_entone)
            output = stdout.read().decode('ascii')
            patron_ip = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
            ip_canal = re.findall(patron_ip, output) 
            
            if ip_canal != []: 
                ip_canal_var = ip_canal[0]
                print(f"Canal sintonizado: {ip_canal_var}")                            
                return ip_canal_var
            else:
                return False                                           
        except (EOFError, TimeoutError, ConnectionResetError, ConnectionRefusedError, paramiko.AuthenticationException, paramiko.SSHException, paramiko.ChannelException, paramiko.ProxyCommandFailure, paramiko.ssh_exception.NoValidConnectionsError) as e:
            print(e)           
    else:
        print(f"deco: {ip_address} no respondio el ping")
        return False
    
# COMIENZO   
t1 = time.perf_counter()

if login():
    # Traigo la lista de canales
    root_channels = api_call('http://172.24.1.4:7780/dataservices/cdk?SP=md_liv.get_channel_list(%27ng%27,%27LIVE%27,%271%27,%27%27,%27N%27,1,1000,?,?,?int%20status)')    
    channel_list = []
    for row in root_channels.iter('row'):
        if row.get('IP_PORT') == '56000' or row.get('IP_PORT') == '2001':
            channel_dict = {}
            if row.get('CHANNEL_ID') in id_canales.channels_ides:       
                channel_dict['NAME'] = row.get('CHANNEL_NAME')
                channel_dict['IP'] = row.get('IP_ADDRESS')
                channel_dict['COUNTER'] = 0
                channel_dict['ID'] = row.get('CHANNEL_ID')       
                channel_list.append(channel_dict)
    
    # Traigo la lista de clientes activos
    root_customers = api_call('http://172.24.1.4:7780/dataservices/cdk?SP=md_cst.get_customer_list(%27ng%27,%271%27,%2710000%27,%271%27,%27%27,?,?,?int%20status)')   
    customer_list = []
    for row in root_customers.iter('row'):
        customer_id = row.get('CUSTOMER_ID')
        customer_status = row.get('STATUS')
        if customer_id != None and customer_status != None:
            if customer_id.startswith(('1')) and customer_status == 'A':
                customer_list.append(customer_id)

    # Traigo la lista de STB's y hago join de las ip de los pertenecientes a clientes activos
    root_ip = api_call('http://172.24.1.4:7780/dataservices/cdk?SP=md_dev.get_device_list(%27ng%27,%276%27,%27A%27,%27n%27,%271%27,%2710000%27,?,?,?int%20status)')    
    kaon_ip_list = []
    entone_ip_list = []
    for row in root_ip.iter('row'):          
        mac = row.get('MAC_ADDRESS')
        ip_address = row.get('IP_ADDRESS')
        customer_device = row.get('CUSTOMER_ID')
        if customer_device in customer_list:
            if ip_address != '0.0.0.0' and ip_address != '':
                stb_counter += 1                                
                if mac.startswith(('743AEF', '44F034', '90F891', '808C97')):
                    kaon_counter += 1
                    kaon_ip_list.append(ip_address) 
                # if mac.startswith(('0003')):
                #     entone_counter += 1
                #     entone_ip_list.append(ip_address)    
    res1 = []
    res2 = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=64) as exec:
        try:
            res1 = exec.map(worker_kaon, kaon_ip_list, timeout=10)
            #res1b = concurrent.futures.wait(res1, timeout=10)
            #res2 = exec.map(worker_entone, entone_ip_list, timeout=10)          
            #res2b = concurrent.futures.wait(res2, timeout=10)
        except (concurrent.futures.TimeoutError, ConnectionResetError) as e:
            print(e)
    res1=list(res1)
    res2=list(res2)
    results = res1 + res2
    
    for r in results:
        if r != False:
            kaon_counter_reached += 1
            for chan in channel_list:
                if str(r) in chan['IP']:
                    chan['COUNTER'] += 1 
else:
    print("No se ejecuto el programa")
    log.write("No se ejecuto el programa\n")
    exit()

t2 = time.perf_counter() 

# Data
total_consulted = kaon_counter + entone_counter
total_active = kaon_counter_reached + entone_counter_reached
exec_time = t2 - t1

log.write("######## RESULTADOS #########\n")
log.write(f"Tiempo de ejecucion: {round((exec_time), 2)}\n")
log.write(f"Cantidad de usuarios activos de TELVGG: {len(customer_list)}\n") 
log.write(f"Total STB's: {stb_counter}\n")
log.write(f"Total muestreo: {total_consulted}\n")
log.write(f"Total kaons: {kaon_counter}\n")
log.write(f"Total kaons que respondieron: {kaon_counter_reached}\n")
log.write(f"Total Entone's: {entone_counter}\n")
log.write(f"Total Entone's que respondieron: {entone_counter_reached}\n")

log.write("######## CANALES #########\n")
for chan in channel_list:
    log.write(f"{chan}\n")

# Grabado en BD
try:
    conn = sqlite3.connect('/usr/local/bin/rating.db')
    cursor = conn.cursor()
    for chan in channel_list:

        cursor.execute("INSERT INTO ratings (ip, name, chan_id, counter, total_stb, total_consulted, total_active, exec_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (chan['IP'], chan['NAME'], chan['ID'], chan['COUNTER'], stb_counter, total_consulted, total_active, exec_time))

    conn.commit()
    conn.close()

except (sqlite3.Error, sqlite3.DatabaseError, sqlite3.IntegrityError, sqlite3.OperationalError, sqlite3.ProgrammingError, sqlite3.Warning) as e:
    log.write(f"{e}\n")

# Finalizacion
logoff()
log.close()
exit()

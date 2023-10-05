import datetime, sqlite3, smtplib
from email.message import EmailMessage

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

show_1 = "Ivision Noticias"
show_2 = "Mañanas JV"

try:
    conn = sqlite3.connect('/usr/local/bin/rating.db')
    cursor = conn.cursor()
    #query for different tv shows x different emissions
    #first
    cursor.execute(f"select AVG(counter), AVG(total_stb), AVG(total_consulted) from ratings where ip = '233.46.39.1' AND date like '{yesterday}%' AND (TIME(date) BETWEEN '17:00' AND '17:30')")
    first_spect_avg, first_stb_avg, first_cons_avg = cursor.fetchone()
    espec_show_1_first = first_spect_avg * first_stb_avg / first_cons_avg
    #second
    cursor.execute(f"select AVG(counter), AVG(total_stb), AVG(total_consulted) from ratings where ip = '233.46.39.1' AND date like '{yesterday}%' AND (TIME(date) BETWEEN '22:00' AND '22:30')")
    second_spect_avg, second_stb_avg, second_cons_avg = cursor.fetchone()
    espec_show_1_second = second_spect_avg * second_stb_avg / second_cons_avg
    #third
    cursor.execute(f"select AVG(counter), AVG(total_stb), AVG(total_consulted) from ratings where ip = '233.46.39.1' AND date like '{today}%' AND (TIME(date) BETWEEN '03:00' AND '03:30')")
    third_spect_avg, third_stb_avg, third_cons_avg = cursor.fetchone()
    espect_show_1_third = third_spect_avg * third_stb_avg / third_cons_avg
    # sum
    espect_show_1 = espec_show_1_first + espec_show_1_second + espect_show_1_third
    #estimate total spectators
    espect_show_1 = int(espect_show_1)
    print(f"Fecha: {yesterday}")
    print("NOTICIERO")
    print(f"Espectadores: {espect_show_1}")
    #rating
    punto = int(first_stb_avg * 0.01)
    rating_show_1 = float(espect_show_1) / punto
    rating_show_1 = "{:.1f}".format(rating_show_1)
    print(f"Rating: {rating_show_1}")

    #query for the other tv show and it's emissions
    #first
    cursor.execute(f"select AVG(counter), AVG(total_stb), AVG(total_consulted) from ratings where ip = '233.46.39.1' AND date like '{yesterday}%' AND (TIME(date) BETWEEN '12:00' AND '13:00');")
    first_spect_avg, first_stb_avg, first_cons_avg = cursor.fetchone()
    espect_show_2_first = first_spect_avg * first_stb_avg / first_cons_avg
    #second
    cursor.execute(f"select AVG(counter), AVG(total_stb), AVG(total_consulted) from ratings where ip = '233.46.39.1' AND date like '{yesterday}%' AND (TIME(date) BETWEEN '17:30' AND '18:30');")
    second_spect_avg, second_stb_avg, second_cons_avg = cursor.fetchone()
    espect_show_2_second = second_spect_avg * second_stb_avg / second_cons_avg
    #third
    cursor.execute(f"select AVG(counter), AVG(total_stb), AVG(total_consulted) from ratings where ip = '233.46.39.1' AND date like '{yesterday}%' AND (TIME(date) BETWEEN '21:00' AND '22:00');")
    third_spect_avg, third_stb_avg, third_cons_avg = cursor.fetchone()
    espect_show_2_third = third_spect_avg * third_stb_avg / third_cons_avg
    #sum
    espect_show_2 = espect_show_2_first + espect_show_2_second + espect_show_2_third
    espect_show_2 = int(espect_show_2)
    print("MAÑANAS JUNTO A VOS")
    print(f"Espectadores: {espect_show_2}")
    #rating
    punto = int(first_stb_avg * 0.01)
    rating_show_2 = float(espect_show_2) / punto
    rating_show_2 = "{:.1f}".format(rating_show_2)
    print(f"Rating: {rating_show_2}")

    conn.close()
except (sqlite3.Error, sqlite3.DatabaseError, sqlite3.IntegrityError, sqlite3.OperationalError, sqlite3.ProgrammingError, sqlite3.Warning) as e:
    print(f"{e}\n")
#make html email to inform each day after
contactos = ['sistemas@telvgg.coop', 'ivision@telvgg.coop']

msg = EmailMessage()
msg['Subject'] = "Rating del dia de ayer"
msg['From'] = "root@rating.coopvgg.com.ar"
msg['To'] = contactos

msg.add_alternative(f"""\n
<!DOCTYPE html>
<html>
    <head>
    </head>
    <body>
        <h1 style="color:salmon;">Numeros del dia {yesterday}</h1>
          <table border="1" bgcolor="lightgray">
            <thead>
                <tr>
                    <th align="center">Programa</th>
                    <th align="center">Rating</th>
                    <th align="center">Espect. promedio</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td align="center">{show_1}</td>
                    <td align="center">{rating_show_1}</td>
                    <td align="center">{espect_show_1}</td>
                </tr>
                 <tr>
                    <td align="center">{show_2}</td>
                    <td align="center">{rating_show_2}</td>
                    <td align="center">{espect_show_2}</td>
                </tr>
            </tbody>
        </table>
    </body>
</html>
""", subtype='html')

with smtplib.SMTP('localhost', 25) as smtp:
    smtp.send_message(msg)

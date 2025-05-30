from datos import excluded, contenido_administracion, contenido_soporte
import sys, logging, smtplib, re
from email.message import EmailMessage
from datetime import datetime, time

logging.basicConfig(filename='/usr/local/bin/autorespuesta_correos/mail_processor.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

recipients_config = {
    "administracion@telvgg.coop": {
        "signature": contenido_administracion,
        "work_hours": {
            "weekdays": (time(7, 30), time(17, 0)),
            "saturday": None,
            "sunday": None
        }
    },
    "contacto@telvgg.coop": {
        "signature": contenido_administracion,
        "work_hours": {
            "weekdays": (time(7, 30), time(17, 0)),
            "saturday": None,
            "sunday": None
        }
    },
    "consulta@telvgg.coop": {
        "signature": contenido_soporte,
        "work_hours": {
            "weekdays": (time(7, 30), time(17, 0)),
            "saturday": None,
            "sunday": None
        }
    },
    "soporte@telvgg.coop": {
        "signature": contenido_soporte,
        "work_hours": {
            "weekdays": (time(7, 30), time(17, 0)),
            "saturday": None,
            "sunday": None
        }
    },
}


def is_off_hours(recipient_email):
    now = datetime.now()
    current_time = now.time()
    weekday = now.weekday()  # 0 = Monday, 6 = Sunday

    # PARA TESTEO
    #weekday=6
    #current_time = time(23, 10)
    #recipient_email=""

    config = recipients_config.get(recipient_email)

    if 0 <= weekday <= 4:
        start, end = config["work_hours"]["weekdays"]
        return current_time < start or current_time > end
    elif weekday == 5:
        saturday_hours = config["work_hours"].get("saturday")
        if saturday_hours is None:
            return True
        else:
            start, end = saturday_hours
            return current_time < start or current_time > end
    elif weekday == 6:
        return True  
    return False

def process_email(sender_email, recipient_email):
    config = recipients_config.get(recipient_email)
    contenido = config["signature"]
    if not sender_email:
        logging.info("Empty from")
    elif sender_email.lower().endswith("@telvgg.coop") or sender_email.lower().endswith("@gapps.telvgg.coop") or sender_email in excluded:
        logging.info(f"Not responding to: {sender_email}")
    else:
        logging.info(f"Autorespuesta a: {sender_email}")
        try:
            msg = EmailMessage()
            msg['Subject'] = "Gracias por comunicarse con TELVGG"
            msg['From'] = recipient_email
            msg['To'] = sender_email

            msg.add_alternative(contenido, subtype='html')

            with smtplib.SMTP('localhost', 25) as smtp:
                smtp.send_message(msg)
        except Exception as e:
            logging.error(f"Fallo envio a: {sender_email}: {e}")

if __name__ == "__main__":
    #El read no funciona porque espera EOF
    #email = sys.stdin.read().strip()

    #Esto fue una prueba pasandole argumento
    #email = sys.argv[1]

    for line in sys.stdin:
        log_line = line.strip()
        if "postfix/smtpd" in log_line and "RCPT from" in log_line:
            sender = re.search(r'from=<([^>]+)>', log_line)
            recipient = re.search(r'to=<([^>]+)>', log_line)
            if sender and recipient:
                sender_email = sender.group(1)
                recipient_email  = recipient.group(1)
                if recipient_email in recipients_config:
                    if is_off_hours(recipient_email):
                        logging.info(log_line)
                        process_email(sender_email, recipient_email)

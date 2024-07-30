# InternetSpeed
Test Internet connection over long time

Omdat een kennis heelwat problemen kende met zijn Internetconnectie en bij mij aanklopte voor hulp, heb ik een applicatie, in Python op Raspberry Pi, geschreven die om de 10 seconden 3 pings stuurt naar en 1: lokale gateway en 2: DNS server van de provider en 3 naar de alomgekende 8.8.8.8 van Google. Alles wegschrijven in CSV file en indien gewenst, op einde van de dag doormailen naar iemand. 
Volgende dag met een 2de applicatie, ook in Python, een kleine statistiek en grapiek maken om alles duidelijk te hebben. Dit een paar weken doen en met info/"bewijzen" naar provider. Ondertussen probleem opgelost door nieuwe verdeeldoos op de paal. 
Nu ook de app ook uitgebreid zodat, indien je een internet-bereikbare SFTP server hebt, je om de x minuten een bestand van x MB kan uploaden en downloaden en zo de Mbps kan meten. 
Ik ga de apps nu gebruiken om eens te kijken of er verschillen in snelheid zijn in mijn straat/wijk en tussen providers. 
Voor zij die dit ook willen doen, in Files/bestanden staat een ZIP file "InternetSpeed" die je kan gebruiken. zou wel fijn en informatief zijn mocht je je resultaten eens laten weten zodat ik eens kan vergelijken. 
NB: door thuis te testen etc ook te weten gekomen dat 1 van mijn 2 switches een stuk (lees 2 maal) trager is. Dus die gaan we vervangen.
NB: Pi laat toe om of via netwerkkabel te testen of via WiFi. Indien via WiFi zou ik als eerste het AP pingen. Zoiets zal voor een V2 zijn

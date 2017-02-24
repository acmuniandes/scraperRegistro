from bs4 import BeautifulSoup
import csv
import html5lib
from urllib.request import urlopen
import schedule
import time
import datetime
import redis
import os
import requests

class clase:
    nombre = ''
    salon = []
    horaInicio=''
    horaFin=''
    dias=''

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36"

def scrape():
    listaClases=[]
    log("solicitando principal")
    page = request("https://registroapps.uniandes.edu.co/scripts/semestre/adm_con_horario_joomla.php")

    soup = BeautifulSoup( page , 'html5lib')

    for unDepartamento in soup.find_all('a'):
        link =''
        link=unDepartamento.get('href')
        
        is_relative_article_link = link.startswith('..')
        if is_relative_article_link:
            nuevolink = "https://registroapps.uniandes.edu.co/scripts" + link.split('..')[1]
        noodles = BeautifulSoup(request(nuevolink),'html5lib')
        nombres = noodles.find_all('td', width='156')

        for casilla in noodles.find_all('td',height='17'):
            contenido = str(casilla.string)
            salon = []
            dias =''
            horarioInicio =''
            horarioFin=''
            if (('.' in contenido and '_' in contenido) or 'NOREQ' in contenido):
                #print('entre a un salon: '+ contenido)
                salon.append(contenido)

            elif('-' in contenido):
                #print('entre a un horario: '+ contenido)
                horario = contenido.split('-')
                horarioInicio = horario[0]
                horarioFin = horario[1]
           #si no contiene el salón o el horario, falta verificar que sea un día
            elif (esDia(contenido) == 1):
                #print('entre a un dia: '+ contenido)
                dias = contenido.replace('    ','')

            if( salon and horarioInicio and horarioFin and dias):
                nuevaClase = clase()
                nuevaClase.salon = salon
                nuevaClase.horaInicio = horarioInicio
                nuevaClase.horaFin = horarioFin
                nuevaClase.dias = dias
                print('Clase nueva: \n' +
                  'Salon: ' + nuevaClase.salon+
                  'Horario: ' + nuevaClase.horaInicio + '-' + nuevaClase.horaFin + 
                  'Días: ' + nuevaClase.dias)
                listaClases.append(nuevaClase)

                dias, horarioInicio, horarioFin, dias = ''
                salon = []
                
            

    #elcsv = serialize_articles(listaArticulos)
    #store(elcsv)
    log("termine")
    print(datetime.datetime.now())

def request(url):
    log("requesting " + url)
    custom_headers = {
        'user-agent' : USER_AGENT ,
        'accept': "text/html;charset=UTF-8"
    }
    response = requests.get(url , headers = custom_headers)
    response.encoding="utf-8"
    return response.text

def log(algo):
    prefix = '[' + timestamp() + '] '
    print( prefix + algo)

def timestamp():
    return datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")

def serialize_articles(lista):
    articulos = map(serialize_article, lista)
    finalCsv =  "titulo,link,contenido,fecha,imagen\n" + '\n'.join(articulos)
    return finalCsv

def serialize_article(article):
    line_elements = [
        article.titulo,
        article.link,
        article.contenido,
        article.fecha,
        article.imagen
    ]
    clean_line_elements = map(applyFormatEscaping , line_elements )
    final_line = ','.join(clean_line_elements)
    return final_line

def applyFormatEscaping(data):
    return  '"' + str(data).replace('"', "'") + '"'

def store(content):
    r = redis.from_url(os.environ.get('REDIS_URL'))
    r.set('news' , content.encode('utf8'))

def esDia(casilla):
    print(casilla)
    if ('Dí' in casilla or 'Horas' in casilla or 'Sal' in casilla):
        return 0
    else:
        if('  L  ' in casilla or '  M  ' in casilla or '  I  ' in casilla or'  J  ' in casilla or '  V  ' in casilla or '  S  ' in casilla):
            return 1

scrape()
schedule.every(5).minutes.do(scrape)
while True:
    schedule.run_pending()
    time.sleep(1)

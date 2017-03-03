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
    salon = []
    horario = []
    dias=[]
    profesores = []
    
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

        contenido = ''

        salon = []
        dias =[]
        horario = []
        profesores = []
            
        for casilla in noodles.find_all('td',height='17'):
            
            contenido = str(casilla.string)
            if (contenido != None):  

                contenido = str(contenido.lstrip().rstrip())
            
                if ((contenido.startswith('.') and ('_' in contenido)) or 'NOREQ' in contenido):
                    salon.append(contenido.lstrip().rstrip())
                    
                elif('-' in contenido):
                    #print('entre a un horario: '+ contenido)
                    horario.append(contenido)

               #si no contiene el salón o el horario, falta verificar que sea un día
                elif (esDia(contenido)):
                    #print('entre a un dia: '+ contenido )
                    dias.append(contenido)

                elif(esNombre(contenido)):
                    profesores.append(contenido)

                if( salon and horario and dias and profesores and contenido == 'Horas'):
                    nuevaClase = clase()
                    nuevaClase.salon = salon
                    nuevaClase.horario = horario
                    nuevaClase.dias = dias
                    nuevaClase.profesores = profesores
                    print('Clase nueva: \n' +
                     'Salones: ' + listaToString(nuevaClase.salon) + '\n' +
                     'Horarios: ' + listaToString(nuevaClase.horario) + '\n' +
                     'Días: ' + listaToString(nuevaClase.dias)+ '\n' +
                     'Profesores: ' + listaToString(nuevaClase.profesores))

                    listaClases.append(nuevaClase)

                    dias = []
                    horario = []
                    dias = []
                    salon = []
                    profesores = []
                
            
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

    cantidadEspacios = 0
    cantidadLetras = 0

    for caracter in casilla:
        if (caracter == ' '):
            cantidadEspacios += 1
        else:
            cantidadLetras += 1

    #Conjetura: la cantidad de espacios en el string es dos veces la cantidad de letras menos 1, por ejemplo:
    # "L" > Cantidad de letras = 1, espacios  = 0, entonces cumple la formula (0 = 2*(1-1))
    # "L  M  V" Cantidad de letras = 3, espacios igual 4, entonces cumple la fórmula (4 = 2(3-1))
    return (cantidadEspacios == 4*(cantidadLetras-1) or cantidadEspacios == 6*(cantidadLetras-1))

def esNombre(casilla):
    if( not esDia(casilla)):
        return ' ' in casilla #esto puede servir porque si hice lstrip() y rstrip(), si es un nombre va a tener AL MENOS 1 espacio


def listaToString(lista):
    return ("[" + ", ".join(map(str, lista)) + "]")


scrape()
schedule.every(5).minutes.do(scrape)
while True:
    schedule.run_pending()
    time.sleep(1)
    #python scraperregistro.py
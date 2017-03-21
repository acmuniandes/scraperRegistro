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
    dias = []
    profesores = []

class salon:
    edificio = ''
    numero = ''
    #REFERENCIA: horarios[a][b] guarda los horarios de un salon, donde b representa la franja horaria y a el día correspondiente
    #Es decir, horarios[1][0] haría referencia a //la primera// una clase del salón los martes (los días se empiezan a contar desde cero)
    horarios = [['' for x in range(1)] for x in range(7)]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.95 Safari/537.36"

def scrape():
    #Inicializo la lista de clases de registro
    listaClases=[]
    
    log("solicitando principal")
    page = request("https://registroapps.uniandes.edu.co/scripts/semestre/adm_con_horario_joomla.php")

    #Hago el request de Registro
    soup = BeautifulSoup(page, 'html5lib')

    #Voy a recorrer cada departamento, buscando las clases
    for unDepartamento in soup.find_all('a'):
        link = ''
        link = unDepartamento.get('href')

        is_relative_article_link = link.startswith('..')
        if is_relative_article_link:
            nuevolink = "https://registroapps.uniandes.edu.co/scripts" + link.split('..')[1]
        #Saco la página del departamento y miro todos los tags 'td' con width = '156'
        noodles = BeautifulSoup(request(nuevolink),'html5lib')

        contenido = ''

        #Variables locales que usaré recorriendo los departamentos
        salon = []
        dias =[]
        horario = []
        profesores = []
        #Variable que me notifica que acabe de leer una clase
        skip = False;

        #Por cada tag que haya encontrado
        for casilla in noodles.find_all('td', height='17'):
        
            contenido = str(casilla.string)
            if (contenido != None):

                contenido = str(contenido.lstrip().rstrip())
              #TODO Mejorar que los .NOREQ y los . no salgan en los salones
                if contenido.startswith('.')  and not 'REQ' in contenido and contenido != '.':
                    salon.append(contenido.lstrip().rstrip())
                    
                elif '-' in contenido and len (contenido) > 2:
                    #print('entre a un horario: '+ contenido)
                    horario.append(contenido)

               #si no contiene el salón o el horario, falta verificar que sea un día
                elif (esDia(contenido)):
                    #print('entre a un dia: '+ contenido )
                    dias.append(contenido)

                elif(esNombre(contenido)):
                    profesores.append(contenido)

                #Si leo el string horas, significa que estoy en una clase nueva
                if(contenido == 'Horas'):
                    skip = True

                if( salon and horario and dias and profesores and skip):
                    nuevaClase = clase()
                    nuevaClase.salon = salon
                    nuevaClase.horario = horario
                    nuevaClase.dias = dias
                    nuevaClase.profesores = profesores
                    print('----Clase nueva---- \n' +
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

                #Reinicio toda la clase actual, porque no encontré nada concluyente (o no hay salón u horario o días)
                if skip:
                    dias = []
                    horario = []
                    dias = []
                    salon = []
                    profesores = []
                    skip = False

    salones = []
    salones = calcularSalonesDelCampus(listaClases)

    print(salonesCampus(salones))
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

    #La cantidad de espacios en el string es de 2 o 4 o 6 o 8 por día. Si hay un solo día, no hay espacios
    #Ejemplos de formato de días: "L", "M      L"; "L    M    I"; "J      V      S"
    return (cantidadEspacios == 2*(cantidadLetras-1) or cantidadEspacios == 4*(cantidadLetras-1) or cantidadEspacios == 6*(cantidadLetras-1) or cantidadEspacios == 8*(cantidadLetras-1))

def esNombre(casilla):
    if(not esDia(casilla)):
        return (' ' in casilla)
        #esto puede servir porque si hice lstrip() y rstrip(), si es un nombre va a tener AL MENOS 1 espacio

def listaToString(lista):
    return ("[" + ", ".join(map(str, lista)) + "]")

def calcularSalonesDelCampus(listaClases):
    listaDeSalonesCampus = []
    for clase in listaClases:
        agregarSalonesPorClase(listaDeSalonesCampus, clase)
    return listaDeSalonesCampus


def agregarSalonesPorClase(listaDeSalones, clase):
    global salon
    for salonDeClase in clase.salon:
        posicion = 0
        existeElSalon = False
        for salonL in listaDeSalones:
            existeElSalon = salonL.edificio in salonDeClase and salonL.numero in salonDeClase #Si el salon tiene el edificio y el numero del salon busacdo, entonces si existe
            if (existeElSalon): #Si existe, simplemente le paso la información de la clase
                agregarClaseASalon(salon, clase.horario[posicion], clase.dias[posicion]) 
                break

        if not existeElSalon: #Si al final de recorrer toda la lista de salones no existe el salon, entonces debo agregarlo a la lista de salones
            nuevo = salon()
            datosSalon = salonDeClase.split('_')
            nuevo.edificio = datosSalon[0]
            try:
                nuevo.numero = datosSalon[1]
            except IndexError:
                print('Clase en el ' + datosSalon[0])
            listaDeSalones.append(nuevo)
            agregarClaseASalon(nuevo, clase.horario[posicion], clase.dias[posicion])
        posicion += 1


def agregarClaseASalon(salon, horario, dias):
    for caracter in dias:#Por cada día, voy a agregar los horarios al salon
        dia = identificarNumeroDia(caracter)
        if (dia >= 0):
            salon.horarios[dia].append(horario)
    

def identificarNumeroDia (letraDia):
    if (letraDia == 'L'):
        return 0
    elif (letraDia == 'M'):
        return 1
    elif (letraDia == 'I'):
        return 2
    elif (letraDia == 'J'):
        return 3
    elif (letraDia == 'V'):
        return 4
    elif (letraDia == 'S'):
        return 5
    elif (letraDia == 'D'):
        return 6
    else:
        return -1

def salonesCampus(listaDeSalones):
    respuesta = ''
    for salon in listaDeSalones:
        print("Voy en: " + salon.edificio + salon.numero)
        respuesta += (
            '----------' + salon.edificio + salon.numero + '---------\n' +
            listaDeListasToString(salon.horarios) +
            '------------------------------\n'
        )
    return respuesta

def identificarDiaNumero(numeroDia):
    if (numeroDia == 0):
        return 'Lunes'
    elif (numeroDia == 1):
        return 'Martes'
    elif (numeroDia == 2):
        return 'Miércoles'
    elif (numeroDia == 3):
        return 'Jueves'
    elif (numeroDia == 4):
        return 'Viernes'
    elif (numeroDia == 5):
        return 'Sabado'
    elif (numeroDia == 6):
        return 'Domingo'
    else:
        return 'AyyLmao'

def listaDeListasToString(listaDeListas):
    i = 0;
    respuesta = ''
    while ( i < len(listaDeListas) ): #Dimensión de los días (voy a ir por todos los días)
        respuesta += '[' + identificarDiaNumero(i) + '] =' + listaToString(listaDeListas[i]) + '\n'
        i += 1
    return respuesta

scrape()
schedule.every(5).minutes.do(scrape)
while True:
    schedule.run_pending()
    time.sleep(1)
    #python scraperregistro.py

 #TODO list:
    #Hay algunos días que se agregan en los profesores, revisar si tiene que ver con la cantidad de espacios
        #En efecto, por ejemplo, en el dpto de ciencias biológicas hay una clase que tiene 8 espacios entre dias ¡Hecho!
        #Toca ver si el número de espacios tiene que ver con algún atributo de la clase (¿por qué decidieron usar diferentes cantidades de espacios?)
    #Hay algunos días que la cantidad de espacios entre días no es consistente // Hasta ahora van espacios de a 2, 4, 6 y 8
    #Algunos salones tienen solamente . en vez de .NOREQ
    #Las clases con .NOREQ no están
    #Existen clases .NOREQ con salon, REGISTRO PLOX, o está mal el scrapeo aparición: Pablo Figueroa al final de ISIS
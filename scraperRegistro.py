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
import json

class clase:

    def __init__(self, pSalones, pDias, pHorario):
        self.salones = pSalones
        self.horario = pHorario
        self.dias = pDias

    def agregarSalon(self, pSalon):
        self.salones.append(pSalon)

    def agregarDias(self, pDias):
        self.dias.append(pDias)
    
    def agegarHorario(self, pHorario):
        self.horario.append(pHorario)
    

class salon:

    def __init__(self, pIdSalon):
        self.idSalon = pIdSalon
        #REFERENCIA: horarios[a][b] guarda los horarios de un salon, donde b representa la franja horaria y a el día correspondiente
        #Es decir, horarios[1][0] haría referencia a //la primera// una clase del salón los martes (los días se empiezan a contar desde cero)
        self.horarios = [['' for x in range(0)] for x in range(7)]

    def agregarHorario(self, pDia, pHorario):
        self.horarios[pDia].append(pHorario)

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
        salonesRaw = []
        diasRaw =[]
        horariosRaw = []
        #Variable que me notifica que acabe de leer una clase
        skip = False;

        #Por cada tag que haya encontrado
        for casilla in noodles.find_all('td', height='17'):
        
            contenido = str(casilla.string)
            if (contenido != None):

                contenido = str(contenido.lstrip().rstrip())
              #TODO Mejorar que los .NOREQ y los . no salgan en los salones
                if contenido.startswith('.')  and not 'REQ' in contenido and contenido != '.':
                    salonesRaw.append(contenido.lstrip().rstrip())
                    
                elif '-' in contenido and len (contenido) > 2:
                    #print('entre a un horario: '+ contenido)
                    horariosRaw.append(contenido)

               #si no contiene el salón o el horario, falta verificar que sea un día
                elif (esDia(contenido)):
                    #print('entre a un dia: '+ contenido )
                    diasRaw.append(contenido)

                #Si leo el string horas, significa que estoy en una clase nueva
                if(contenido == 'Horas'):
                    skip = True

                if( salonesRaw and horariosRaw and diasRaw and skip):
                    nuevaClase = clase(salonesRaw, diasRaw, horariosRaw)
                    #print('----Clase nueva---- \n' +
                     #     'Salones: ' + listaToString(nuevaClase.salones) + '\n' +
                      #    'Horarios: ' + listaToString(nuevaClase.horario) + '\n' +
                       #   'Días: ' + listaToString(nuevaClase.dias)
                         #)

                    listaClases.append(nuevaClase)

                    diasRaw = []
                    horariosRaw = []
                    diasRaw = []
                    salonesRaw = []

                #Reinicio toda la clase actual, porque no encontré nada concluyente (o no hay salón u horario o días)
                if skip:
                    diasRaw = []
                    horariosRaw = []
                    diasRaw = []
                    salonesRaw = []
                    skip = False

    salones = calcularSalonesDelCampus(listaClases)

    with open('Classrooms.csv', 'w') as myfile:
        writer = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        for noSeQue in salones:
            info = [noSeQue.idSalon, listaDeListasToString(noSeQue.horarios)]
            writer.writerow(info)
    myfile.close

    data = {}

    serializeClassrooms(salones, 'OccupiedClassrooms.json', data)

    #Optimizaciones de memoria
    soup = ''
    listaClases = ''
    data = {}

    calcularDisponibles(salones)

    serializeClassrooms(salones, 'FreeClasroomsNotOpt.json', data)

    optimizarDisponibles(salones)

    serializeClassrooms(salones, 'FreeClasrooms.json', data)

    log("termine")
    print(datetime.datetime.now())

def request(url):
    log("requesting " + url)
    custom_headers = {
        'user-agent' : USER_AGENT,
        'accept': "text/html;charset=UTF-8"
    }
    response = requests.get(url, headers = custom_headers)
    response.encoding= "utf-8"
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

def calcularSalonesDelCampus(pListaClases):
    listaDeSalonesCampus = []
    for claseL in pListaClases:
        agregarSalonesPorClase(listaDeSalonesCampus, claseL)
    return listaDeSalonesCampus


def agregarSalonesPorClase(listaDeSalones, pClase):
    posicion = 0
    for salonDeClase in pClase.salones:
        existeElSalon = False
        for salonL in listaDeSalones:
            existeElSalon = salonL.idSalon == salonDeClase #Si el salon tiene el id del salon busacdo, entonces si existe
            if (existeElSalon): #Si existe, simplemente le paso la información de la clase
                #print ("A " + salonL.idSalon + " le agregué [" + clase.dias[posicion] +"]  = " + clase.horario[posicion])
                try:
                    agregarClaseASalon(salonL, pClase.horario[posicion], pClase.dias[posicion]) 
                except IndexError:
                    print ("A " + salonL.idSalon + " le intenté agregar " + listaToString(pClase.dias) +"[" + str(posicion) + "]"  + listaToString(pClase.horario) + "[" + str(posicion) + "] Y se cagó por índice")
                break

        if not existeElSalon: #Si al final de recorrer toda la lista de salones no existe el salon, entonces debo agregarlo a la lista de salones
            nuevo = salon(salonDeClase)
            agregarClaseASalon(nuevo, pClase.horario[posicion], pClase.dias[posicion])
            listaDeSalones.append(nuevo)
            print (nuevo.idSalon)
        posicion += 1
        


def agregarClaseASalon(pSalon, pHorario, pDias):
    for caracter in pDias:#Por cada día, voy a agregar los horarios al salon
        dia = identificarNumeroDia(caracter)
        if dia >= 0 and (not pHorario in pSalon.horarios[dia]): #Si el día es un índice válido y si el horario NO está en la lista horarios, entonces lo agrego
            pSalon.agregarHorario(dia, pHorario) #Esto lo hago para no tener muchos horarios repetidos para el mismo salón
            print ("A " + pSalon.idSalon + " le agregué [" + caracter +"]  = " + pHorario)
    

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
    for salonL in listaDeSalones:
        print("Voy en: " + salonL.edificio + salonL.numero)
        respuesta += (
            '----------' + salonL.edificio + salonL.numero + '---------\n' +
            listaDeListasToString(salonL.horarios) +
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
        respuesta += '[' + identificarDiaNumero(i) + '] =' + listaToString(listaDeListas[i]) + ' '
        i += 1
    return respuesta

def generarArregloGeneral():
    iteracion = (2200 - 630)/10
    arregloTodosLosHorarios = []
    i = 0
    while i < iteracion:
        horarioNuevo = 630 + i*10
        if esHoraValida(horarioNuevo):
            arregloTodosLosHorarios.append(horarioNuevo)
        i+=1 
    return arregloTodosLosHorarios

def quitarDisponibilidad(horario, arregloDia):
    valores = horario.split('-')
    k = 0
    while k < len(valores): 
        valores[k] = valores[k].lstrip().rstrip()
        k += 1
    inicioClase = int(valores[0])
    finalClase = int(valores[1])

    deboEliminar = False
    horariosAEliminar = []
    for franjaHoraria in arregloDia:
        if franjaHoraria == inicioClase:
            deboEliminar = True
        elif franjaHoraria == finalClase:
            deboEliminar = False
            horariosAEliminar.append(franjaHoraria)
            break
        if deboEliminar:
            horariosAEliminar.append(franjaHoraria)
    
    for eliminar in horariosAEliminar:
        arregloDia.remove(eliminar)

def calcularDisponibles(pSalones):
    #Hago esto para no tener que calcular el arreglo general cada vez
    variableEstado = generarArregloGeneral()
    salonesDisponibles = [[None for x in range(0)] for x in range(7)]

    for cadaSalon in pSalones:
        i = 0
        for dia in cadaSalon.horarios:
            horariosDisponibles = variableEstado[:] #Para que no se haga referencia al mismo estado
            if dia: #Checking list emptyness
                print("longitud del día: " + str(len(dia)))
                for horario in dia:
                    quitarDisponibilidad(horario, horariosDisponibles)
                cadaSalon.horarios[i] = horariosDisponibles
            else:
                print("entré a pythnic empty list")
                cadaSalon.horarios[i] = horariosDisponibles
            i+=1;
    
def serializeClassrooms(classrooms, fileName, emptyDirectory):
    with open(fileName, 'w') as outFile:
        for salonFinal in classrooms:
            emptyDirectory[salonFinal.idSalon] = salonFinal.horarios
        json.dump(emptyDirectory, outFile)
    outFile.close

def esHoraValida(hora):
    horaStr = str(hora)
    long = len(horaStr)
    horaStr = horaStr[long-2:long]
    if (int(horaStr) < 60):
        return True
    return False

def optimizarDisponibles(pSalones):
     for cadaSalon in pSalones:
        i = 0
        for dia in cadaSalon.horarios:
            if dia: #Si la lista no está vacía
                cadaSalon.horarios[i] = optimizarContinuidad(dia)
            else:
                cadaSalon.horarios[i] = "C Mamó :("
            i += 1
        
def optimizarContinuidad(horario):
    horarioOptimizado = []
    i = 0
    esIntervaloContinuo = False
    print (len(horario))
    while i < len(horario)-1:
        if not esIntervaloContinuo:
            esIntervaloContinuo = esHorarioContinuo(horario[i], horario[i+1])
            horarioOptimizado.append(horario[i])
        else:
            esIntervaloContinuo = esHorarioContinuo(horario[i], horario[i+1])
            if not esIntervaloContinuo:
                horarioOptimizado.append(horario[i])
        i += 1
    horarioOptimizado.append(horario[-1])#Agrego el último elemento
    return horarioOptimizado

#Horario 1 es el más temprano
#Horario 2 es el más tarde
def esHorarioContinuo(horario1, horario2):
    hayCambioHora = hayCambioDeHora(horario1,horario2)
    if hayCambioHora:
        if (int(horario2) - int(horario1) == 50):
            return True
        return False
    else:
        return int(horario2) - int(horario1) == 10


def hayCambioDeHora(horario1, horario2):
    hora1 = int(str(horario1)[len(str(horario1))-3])
    hora2 = int(str(horario2)[len(str(horario2))-3])

    if abs(hora1-hora2) == 1 or abs(hora1-hora2) == 9:
        return True
    return False

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
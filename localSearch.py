import csv

from scraperRegistro import salon

class salonesCampus:

    salones = []
    def __init__(self):
        cargarSalones(salones)

def cargarSalones(pSalones):

    with open('test.csv') as raw:
        reader = csv.reader(raw, delimiter = ',')
        for fila in reader:
            nuevoSalon = salon(fila[0])
            nuevoSalon.agregarHorari



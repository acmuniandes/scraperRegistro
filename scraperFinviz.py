from bs4 import BeautifulSoup
import csv
import html5lib
from urllib.request import urlopen
import schedule
import time

class registro:
    fecha=''
    valor=''
    contenido=''
listaRegistros=[]

def scrape():
    soup = BeautifulSoup(urlopen("http://finviz.com/futures.ashx"),'lxml')
    a = soup.find_all('script', type="text/javascript", src="")
    # print(soup)
    for i in a:
        print (i)
    # for unArticulo in soup.find_all('div',class_="main_article"):
    #     nuevoArticulo=articulo()
    #     nuevoArticulo.titulo=unArticulo.a.string
    #     nuevoArticulo.link=unArticulo.a['href']
    #     nuevoArticulo.contenido=""
    #     nuevoArticulo.contenido = (noodles.find('div',id="contenido"))
    #     listaArticulos.append(nuevoArticulo)

    # with open("data.csv", "w") as f:
    #     writer = csv.writer(f)
    #     # writer.writerow(["fecha", "", "contenido"])
    #     for a in listaArticulos:
    #         writer.writerow([a.titulo,a.link, a.contenido])


scrape()
# schedule.every(1).minutes.do(job)
#
# while True:
#     schedule.run_pending()
#     time.sleep(1)

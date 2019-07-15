from qengines.QueryEngine import QueryEngine
import urllib.request
import urllib.parse
import bs4
import re
import datetime
import unidecode
from collections import deque # para parsear horarios

DIAS = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']

def limpiar_string(s):
    return s.replace('\n','').strip()

class UcampusEngine(QueryEngine):

    def __init__(self):
        super().__init__("https://ucampus.uchile.cl/m/")

    def query(self, inquired):
        '''Consulta el Catalogo de Cursos de Ucampus del semestre dado.
           Retorna la lista de departamentos con su respectivo código y
        parámetro para conseguir por GET.
            Ej de uso:
            ue = UcampusEngine()
            inquired = {'semestre':'20172', 'unidad': 'fcfm'}
            res = ue.query(inquired) # json de departamentos
        '''
        return super().query(inquired)

    def fetch(self, inquired):
        unidad = inquired.get('unidad', 'fcfm')
        url_unidad = self.source + unidad + '_catalogo/'
        self.url_catalogo = url_unidad
        semestre = inquired.get('semestre', False)
        if semestre:
            url_unidad += '?semestre='+semestre
        response = urllib.request.urlopen(url_unidad)
        return response

    def parse(self, response, inquired):
        soup = bs4.BeautifulSoup(response, 'html.parser')
        uls = soup.findAll('ul')
        ul_subunidades = uls[4] # Grr
        subunidades = []
        for li in ul_subunidades.findAll('li'):
            anchor = li.a
            if anchor is None:
                break
            param = anchor.get('href')
            nombre_cod = li.a.text
            nombre = ""
            cod = ""
            if '-' in nombre_cod:
                toks = nombre_cod.split('-')
                cod = toks[0].strip()
                nombre = toks[1].strip()
            semestre = inquired.get('semestre', False)
            if not semestre:
                idx_start = param.find('semestre=') + len('semestre=')
                idx_end = param.find('&')
                semestre = param[idx_start:idx_end]
            subunidad = {'param': param,
                         'url_catalogo': self.url_catalogo,
                         'semestre': semestre,
                         'nombre_codigo': nombre_cod,
                         'nombre_depto': nombre,
                         'codigo_depto': cod}
            subunidades.append(subunidad)
        return subunidades

    def query_all_subunidades(self, inquired):
        subunidades = self.query(inquired)
        for subunidad in subunidades:
            due = DeptoUcampusEngine(subunidad)
            catalogo_subunidad = due.query({})
            subunidad['cursos'] = catalogo_subunidad['cursos']
        now = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        res = {'subunidades': subunidades, 'fecha_descarga': now, 'ok': False}
        if len(subunidades) > 0:
            semestre = subunidades[0]['semestre']
            unidad = inquired.get('unidad', 'fcfm')
            res.update({'semestre': semestre, 'unidad': unidad, 'ok': True})
        return res

class DeptoUcampusEngine(QueryEngine):

    def __init__(self, subunidad):
        source_prefix = subunidad.get('url_catalogo', 'https://ucampus.uchile.cl/m/fcfm_catalogo/')
        url = source_prefix + subunidad['param']
        super().__init__(url) # el self.source
        self.semestre = subunidad['semestre']
        self.nombre_depto = subunidad['nombre_depto']
        self.codigo_depto = subunidad['codigo_depto']

    def query(self, inquired):
        return super().query(inquired)

    def fetch(self, inquired):
        return urllib.request.urlopen(self.source)

    def parse(self, response, inquired):
        soup = bs4.BeautifulSoup(response, 'html.parser')

        h2_with_id = [tag for tag in soup.findAll('h2') if 'id' in tag.attrs]
        cod_cursos = [tag['id'] for tag in h2_with_id if tag['id'] != 'titulo']

        dict_depto = {'nombre_depto': self.nombre_depto,
                      'codigo_depto': self.codigo_depto,
                      'cursos': []}

        tablas = soup.findAll('table')
        for codigo_curso, tabla in zip(cod_cursos, tablas):
            curso = self._parse_curso(soup, codigo_curso, tabla)
            dict_depto['cursos'].append(curso)

        return dict_depto

    def _parse_curso(self, soup, codigo_curso, tabla):
        tag_nombre_y_codigo = soup.find('h2', {'id': codigo_curso})

        try: #quito el <a href... de Programa del Curso, lo guardo aparte
            tag_programa = tag_nombre_y_codigo.a.extract()
            link_programa = tag_programa['href']
        except AttributeError:
            link_programa = ""

        try: # no sé qué hace esto... parece que de momento, nada
            tag_nombre_y_codigo.em.extract()
        except AttributeError:
            pass

        nombre_y_codigo = tag_nombre_y_codigo.text.replace('\n','').replace('\t','')
        codigo, nombre = nombre_y_codigo.split(" ", 1)

        dict_curso = {'nombre_curso': nombre,
                      'codigo_curso': codigo,
                      'nombre_y_codigo': nombre_y_codigo,
                      'url_programa': link_programa,
                      'secciones': []}

        tag = tag_nombre_y_codigo
        tags_datos_raw = tag.find_next('dl')
        tags_keys = tags_datos_raw.findAll('dt') #UD, Requisitos, Equivalencias...
        for t in tags_keys:
            try:
                key = t.text
                value = t.findNextSibling('dd').text
                dict_curso[unidecode.unidecode(key)] = value
            except AttributeError:
                print("Error de atributo extrayendo datos en ",codigo_este_curso)
                break

        rows_secciones = tabla.tbody.findAll('tr')
        for row_seccion in rows_secciones:
            seccion = self._parse_seccion(row_seccion)
            dict_curso['secciones'].append(seccion)

        return dict_curso

    def _parse_seccion(self, row_seccion):
        datos_seccion = row_seccion.findAll('td')

        lista_profes = []
        tags_profes_seccion = datos_seccion[1].findAll('h1')
        for tag_profe in tags_profes_seccion:
            lista_profes.append( tag_profe.text.strip() )

        dict_seccion = {'profes_seccion': lista_profes,
                        'cupo_seccion': limpiar_string(datos_seccion[2].text),
                        'ocupados_seccion': limpiar_string(datos_seccion[3].text)
                       }

        horario_raw = datos_seccion[4]

        #el siguiente es un truco feisimo para quitar tildes unicode...
        # (el comentario anterior lo tengo desde Python 2.7, no sé si
        #                                           sigue sirviendo de algo)
        horario_raw = repr(horario_raw).replace('\\t','').replace('\\n','').replace('\\r','')[4:-5].lower()

        if horario_raw == "":
            return dict_seccion

        # seguirá siendo necesario esto? no lo sé
        horario_raw = horario_raw.replace('\\xe1','a').replace('\\xe9','e').replace('\\xed','i')\
                          .replace('\\xf3','o').replace('\\xfa','u').replace('\\xf1','nh').replace('\\xc1','A')\
                          .replace('\\xc9','E').replace('\\xcd','I').replace('\\xbf','O').replace('\\xda','U')\
                          .replace('\\xfc','u').replace('\\xdc','U')

        lista_horario = []
        for entrada in horario_raw.split('<br/>'):
            colon = entrada.find(':')
            tipo = entrada[:colon] # 'catedra', 'auxiliar', 'laboratorio',
            tipo = unidecode.unidecode(tipo)  # 'catedra', 'auxiliar', 'laboratorio',
                                              #   'control', 'semana', u otros

            dias = entrada[colon+2:]

            # No nos interesa el horario si incluye semanas
            idx_semana = dias.find('semana')
            if idx_semana != -1:
                dias = dias[:idx_semana]

            dias = dias.strip()
            tokens = deque(dias.split(' '))

            dia = tokens.popleft()
            while len(tokens) != 0:
                if dia not in DIAS:
                    raise ValueError('Se esperaba un día en vez de \'%s\'' % (dia))

                next_tok = tokens.popleft()
                while next_tok not in DIAS:
                    hora_ini = next_tok.replace(',', '')
                    tokens.popleft() # -
                    hora_fin = tokens.popleft().replace(',', '')

                    dict_bloque = {'tipo_bloque': tipo,
                                   'dia': dia,
                                   'inicio': hora_ini,
                                   'fin': hora_fin}
                    lista_horario.append(dict_bloque)

                    try:
                        next_tok = tokens.popleft()
                    except IndexError:
                        # si no quedan tokens, salimos en seguida
                        break
                # Si salimos del while, next_tok es un dia
                dia = next_tok
            '''
            # Bucle antiguo para parsear horarios
            # (este código lo venía arrastrando desde mallador_v2)
            
            item = item.split(" ")
            len_item = len(item)
            indices = range(1, len_item, 4) # es un for "a la C", necesito jugar con los indices mas abajo
            k = 0
            import pdb
            pdb.set_trace()
            
            try:
                while k < len(indices):
                    j = indices[k]
                    if item[j][:6] == "semana": # no quiero parsear semanas
                        k = len(indices)
                        continue
                    dia = item[j]   # 'lunes', 'martes', ...
                    t_i = item[j+1]
                    t_f = item[j+3].replace(',','').replace(';','')

                    dict_bloque2 = None
                    if j+4 < len_item:
                        if item[j+4][0].isdigit(): #a veces un mismo dia tiene 2 bloques
                            t_i2 = item[j+4].replace(',','').replace(';','')
                            try:
                                t_f2 = item[j+6].replace(',','').replace(';','')
                            except:
                                import pdb
                                pdb.set_trace()
                            dict_bloque2 = {'tipo_bloque': tipo,
                                            'dia': dia,
                                            'inicio': t_i2,
                                            'fin': t_f2}

                    dict_bloque = {'tipo_bloque': tipo,
                                   'dia': dia,
                                   'inicio': t_i,
                                   'fin': t_f}

                    lista_horario.append(dict_bloque)
                    k+=1
                    if dict_bloque2 != None:
                        lista_horario.append(dict_bloque2)
                        k+=2 #<-- juego de indices
            except UnboundLocalError as e:
                print("Error en el for 'a la C'")
                print("\tk: {} - tipo: {}".format(k, type(k)))
                raise e
            '''

        dict_seccion['horario'] = lista_horario
        return dict_seccion


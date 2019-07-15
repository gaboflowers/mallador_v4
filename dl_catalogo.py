#!/usr/bin/python3
from CatalogueEngine import UcampusEngine
from datetime import datetime
import sys, os, json
import stat # para os.chmod

CATALOGOS_PATH = 'catalogos/'
ERROR_FILE = './logs/dl_error.log'

def current_date():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def guardar_error(error):
    with open(ERROR_FILE, 'a') as f:
        f.write(current_date()+' '+error+'\n')

def descargar(semestre, unidad):
    ue = UcampusEngine()
    inquired = {'semestre': semestre,
                'unidad': unidad}
    cat = ue.query_all_subunidades(inquired)
    if not cat['ok']:
        guardar_error('Error al descargar %s %s' % (unidad,semestre))
        return False
    else:
        return cat


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Uso: %s [semestre] [unidad]' % sys.argv[0])
        exit()

    semestre = sys.argv[1]
    unidad = sys.argv[2]

    fname_no_ext = 'catalogo_%s_%s' % (unidad, semestre)
    fname = fname_no_ext+'.json'
    fpath = CATALOGOS_PATH + fname


    try:
        cat = descargar(semestre, unidad)
    except Exception as e:
        print(repr(e))
        print('fail')
        exit()

    printed = False
    if cat:
        try:
            if os.path.isfile(fpath):
                new_name = CATALOGOS_PATH + fname_no_ext + \
                        '_' + current_date() + '.json'
                os.rename(fpath, new_name)

            with open(fpath, 'w') as f:
                json.dump(cat, f)

            os.chmod(fpath, 0o755)
            print('ok')
            printed = True
            exit()
        except Exception as e:
            print(repr(e))
            if not printed:
                print('fail')
    else:
        print('fail')


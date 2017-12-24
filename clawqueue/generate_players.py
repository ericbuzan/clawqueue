import sqlite3
from random import randint, choice
from time import sleep
from shutil import copy
from time import strftime

def generate():
    names = ['Alberto','Beryl','Chris','Debby','Ernesto','Florence','Gordon','Helene','Isaac', \
        'Joyce','Kirk','Leslie','Michael','Nadine','Oscar','Patty','Rafael','Sara','Tony','Valerie', \
        'William','Andrea','Barry','Chantal','Dorian','Erin','Fernand','Gabrielle','Humberto','Imelda', \
        'Jerry','Karen','Lorenzo','Melissa','Nestor','Olga','Pablo','Rebekah','Sebastien','Tanya', \
        'Van','Wendy','Arthur','Bertha','Cristobal','Dolly','Edouard','Fay','Gonzalo','Hanna','Isaias', \
        'Josephine','Kyle','Laura','Marco','Nana','Omar','Paulette','Rene','Sally','Teddy','Vicky','Wilfred']
    try:
        copy('players.db','players'+strftime('-%Y%m%d-%H%M%S')+'.db')
    except FileNotFoundError:
        print('old db not found, not backing up')
    with sqlite3.connect('players.db') as db, open('schema.sql') as schema_file:
        db.executescript(schema_file.read())
        while names != []:
            name = choice(names)
            names.remove(name)
            while True:
                badgeid = randint(1001,19999)
                if not(db.execute('SELECT badgeid FROM players where badgeid=?',(badgeid,)).fetchone()):
                    break
            db.execute('INSERT INTO players (name,badgeid) VALUES (?,?)', [name, badgeid])
        db.commit()

if __name__ == '__main__':
    generate()
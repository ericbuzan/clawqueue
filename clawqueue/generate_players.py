import sqlite3
from random import randint
from time import sleep

def generate():
    names = ['Arlene','Bret','Cindy','Don','Emily','Franklin','Gert','Harvey','Irma','Jose','Katia','Lee','Maria','Nate','Ophelia','Philippe','Rina','Sean','Tammy','Vince','Whitney']

    with sqlite3.connect('players.db') as db, open('schema.sql') as schema_file:
        db.executescript(schema_file.read())
        for i,name in enumerate(names):
            badgeid = 1000+i*50+randint(0,49)
            db.execute('INSERT INTO players (name,badgeid) VALUES (?,?)', [name, badgeid])
        sleep(1)
        db.commit()

if __name__ == '__main__':
    generate()
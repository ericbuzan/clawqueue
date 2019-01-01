# all the imports
import os
import sqlite3
import math
import datetime
from flask import Flask, request, session, g, redirect, \
    url_for, abort, render_template, flash
from random import randint
from shutil import copy
from time import strftime
from generate_players import generate as generate_players
from shutil import copy


app = Flask(__name__) # create the application instance :)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'players.db'),
    SECRET_KEY='Sunny is a very nice kitty.',
    DEBUG = True
))

PEOPLE_IN_QUEUE = 10
MAXNUM_TOPSCORES = 10
NAMES_PER_ROW = 2
LATE_TIME = 5000
WARN_TIME = 10

def connect_db():
    """Connects to the specific database."""
    con = sqlite3.connect(app.config['DATABASE'])
    con.row_factory = sqlite3.Row
    return con

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def hello():
    return 'Welcome to CLAWQUEUE!'

@app.route('/scoreboard')
def scoreboard():
    db = get_db()
    num_topscores = 0
    topscores = []
    the_top_score = db.execute('SELECT max(score) from players').fetchone()[0]
    while True: 
        people_with_this_score = db.execute('SELECT name,badgeid FROM players where score=? ORDER BY updated',(the_top_score,)).fetchall()
        if len(people_with_this_score) != 0:
            num_topscores = num_topscores + math.ceil(len(people_with_this_score)/NAMES_PER_ROW)
            if num_topscores > MAXNUM_TOPSCORES:
                break
            topscores.append((the_top_score, people_with_this_score,len(people_with_this_score)))
        the_top_score = the_top_score - 1
        if the_top_score == 0:
            break
    queued = db.execute('SELECT name, badgeid, updated FROM players where status="queued" ORDER BY qid').fetchall()
    playing = db.execute('SELECT name, badgeid, updated FROM players where status="playing" ORDER BY qid').fetchall()

    return render_template('scoreboard.html', playing=playing, topscores=topscores, queued=queued, NAMES_PER_ROW=NAMES_PER_ROW)

@app.route('/scoreboard_nonwide')
def scoreboard_nonwide():
    db = get_db()
    num_topscores = 0
    topscores = []
    the_top_score = db.execute('SELECT max(score) from players').fetchone()[0]
    while True: 
        people_with_this_score = db.execute('SELECT name,badgeid FROM players where score=? ORDER BY updated',(the_top_score,)).fetchall()
        if len(people_with_this_score) != 0:
            num_topscores = num_topscores + math.ceil(len(people_with_this_score)/NAMES_PER_ROW)
            if num_topscores > MAXNUM_TOPSCORES:
                break
            topscores.append((the_top_score, people_with_this_score,len(people_with_this_score)))
        the_top_score = the_top_score - 1
        if the_top_score == 0:
            break
    queued = db.execute('SELECT name, badgeid, updated FROM players where status="queued" ORDER BY qid').fetchall()
    playing = db.execute('SELECT name, badgeid, updated FROM players where status="playing" ORDER BY qid').fetchall()

    return render_template('scoreboard _nonwide.html', playing=playing, topscores=topscores, queued=queued)


@app.route('/admin_panel')
def admin_panel():
    db = get_db()
    command = request.args.get('command')
    if command != None:
        badgeid = int(request.args.get('id')) if request.args.get('id') else None
        name = request.args.get('name')
        if command == 'add_player':
            if db.execute('SELECT badgeid FROM players where badgeid=?',(badgeid,)).fetchone():
                flash('Error: Badge ID already added')
            else:
                db.execute('INSERT INTO players (name,badgeid) VALUES (?,?)', [name, badgeid])
                db.execute("INSERT INTO updates (message) VALUES (?)", ('New player: %s %s' % (name, badgeid),))
                flash ('%s %s added!' % (name, badgeid))
        elif command == "remove":
            db.execute('DELETE FROM players where badgeid = ?',(badgeid,))
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Removed player: %s %s' % (name, badgeid),))
            flash ('%s %s removed!' % (name, badgeid))
        elif command == "fillqueue":
            fill_queue()
            flash('Queue filled!')
        elif command == "emptyqueue":
            empty_queue()
            flash('Queue emptied!')
        elif command == "wipe":
            wipe()
            flash('Everything deleted! (But it''s backed up)')
        db.commit()
        return redirect(url_for('admin_panel'))
    else:
        players = db.execute('SELECT name, badgeid, updated FROM players ORDER BY badgeid').fetchall()
        return render_template('admin_panel.html',players=players)

@app.route('/get_messages')
def get_messages():
    db = get_db()
    messages = db.execute("SELECT * FROM updates ORDER BY update_time DESC LIMIT 10")
    return render_template('messages.html',messages=messages)


@app.route('/admin_queue')
def admin_queue():
    db = get_db()
    command = request.args.get('command')
    if command != None:
        badgeid = int(request.args.get('id'))
        name = db.execute("SELECT name FROM players where badgeid=?",(badgeid,)).fetchone()[0]
        print("command %s on player %s" % (command, badgeid))
        if command in ['unkick','forcequeue']:
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Player forced into queue: %s %s' % (name, badgeid),))
            db.execute("UPDATE players SET status='queued', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'kick':
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Player kicked: %s %s' % (name, badgeid),))
            db.execute("UPDATE players SET status='kicked', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'startplay':
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Now playing: %s %s' % (name, badgeid),))
            db.execute("UPDATE players SET status='playing', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'finish':
            score = int(request.args.get('score'))
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Score update: %s %s got %s points' % (name, badgeid, score),))
            db.execute("UPDATE players SET status='finished', score=?, updated=datetime('now','localtime') WHERE badgeid=?;",(score,badgeid))
        else:
            db.execute("INSERT INTO updates (message) VALUES (?)", ('not implemented: command %s on player %s' % (command, badgeid),))
            #flash('not implemented: command %s on player %s' % (command, badgeid))
        fill_queue()
        db.commit()
        return redirect(url_for('admin_queue'))

    else:
        playing = db.execute("SELECT * FROM players WHERE status == 'playing' ORDER BY qid").fetchall()
        queued = db.execute("SELECT * FROM players WHERE status == 'queued' ORDER BY qid").fetchall()
        inactive = db.execute("SELECT * FROM players WHERE status == 'inactive' ORDER BY qid").fetchall()
        player_data = playing + queued + inactive
        kicked = db.execute("SELECT * FROM players WHERE status='kicked' ORDER BY badgeid").fetchall()
        finished = db.execute("SELECT * FROM players WHERE status='finished' ORDER BY score DESC").fetchall()
        messages = db.execute("SELECT * FROM updates ORDER BY update_time DESC LIMIT 10")
        return render_template('admin_queue.html',player_data=player_data,kicked=kicked,finished=finished,messages=messages)

@app.route('/generate')
def generate():
    generate_players()
    return redirect(url_for('admin_queue'))


def fill_queue():
    db = get_db()
    queued_ids = db.execute("SELECT badgeid FROM players WHERE status='queued';").fetchall()
    waiting_ids = db.execute("SELECT badgeid FROM players WHERE status='inactive';").fetchall()
    number_to_queue = min([PEOPLE_IN_QUEUE-len(queued_ids), len(waiting_ids)])
    for i in range(number_to_queue):
        new_in_queue = db.execute("SELECT name, badgeid, min(qid) FROM players WHERE status='inactive'").fetchone()
        name, newid, queue_no = new_in_queue
        db.execute("INSERT INTO updates (message) VALUES (?)", ('Called to queue: %s %s' % (name, newid),))
        db.execute("UPDATE players SET status='queued', updated=datetime('now','localtime') \
            WHERE qid=(SELECT min(qid) FROM players WHERE status='inactive') ;")
    db.commit()

def empty_queue():
    db = get_db()
    db.execute("INSERT INTO updates (message) VALUES (?)", ('All players set to inactive',))
    db.execute("UPDATE players SET status='inactive', updated=datetime('now','localtime') WHERE status == 'playing' OR status == 'queued';")
    db.commit()

def wipe():
    try:
        copy('players.db','players'+strftime('-%Y%m%d-%H%M%S')+'.db')
    except FileNotFoundError:
        print('old db not found, not backing up')
    with sqlite3.connect('players.db') as db, open('schema.sql') as schema_file:
        db.executescript(schema_file.read())
        db.commit()


if __name__ == '__main__':
    app.run(host= '0.0.0.0')
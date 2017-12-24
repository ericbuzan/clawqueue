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

PEOPLE_IN_QUEUE = 5
PEOPLE_PLAYING = 3
MAXNUM_TOPSCORES = 10
NAMES_PER_ROW = 2
LATE_TIME = 5000
WARN_TIME = 10

def connect_db():
    """Connects to the specific database."""
    con = sqlite3.connect(app.config['DATABASE'])
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
        people_with_this_score = db.execute('SELECT name,badgeid FROM players where score=? ORDER BY updated DESC',(the_top_score,)).fetchall()
        if len(people_with_this_score) != 0:
            num_topscores = num_topscores + math.ceil(len(people_with_this_score)/NAMES_PER_ROW)
            if num_topscores > MAXNUM_TOPSCORES:
                break
            topscores.append((the_top_score, people_with_this_score))
        the_top_score = the_top_score - 1
        if the_top_score == 0:
            break
    player_data_temp = db.execute('SELECT name, badgeid, updated FROM players where status="called" ORDER BY updated').fetchall()
    player_data_temp = [list(x) for x in player_data_temp]
    called = []
    for data in player_data_temp:
        thyme = datetime.datetime.strptime(data[2],'%Y-%m-%d %H:%M:%S') 
        delta = datetime.datetime.now() - thyme
        if delta.seconds > LATE_TIME:
            data.append('late')
        elif delta.seconds > WARN_TIME:
            data.append('warn')
        else:
            data.append('okay')
        called.append(data)
    soon = db.execute('SELECT name, badgeid FROM players where status="inactive" ORDER BY updated LIMIT 10').fetchall()
    return render_template('scoreboard.html', topscores=topscores, called=called, soon=soon,NAMES_PER_ROW=NAMES_PER_ROW)

@app.route('/add_player')
def add_player():
    db = get_db()
    command = request.args.get('command')
    if command != None:
        badgeid = int(request.args.get('id'))
        name = request.args.get('name')
        if command == 'add_player':
            if len(name) > 12:
                flash('Error: Name is too long')
            elif db.execute('SELECT badgeid FROM players where badgeid=?',(badgeid,)).fetchone():
                flash('Error: Badge ID already added')
            else:
                db.execute('INSERT INTO players (name,badgeid) VALUES (?,?)', [name, badgeid])
                db.execute("INSERT INTO updates (message) VALUES (?)", ('New player: %s %s' % (name, badgeid),))
                flash ('%s %s added!' % (name, badgeid))
        elif command == "remove":
            db.execute('DELETE FROM players where badgeid = ?',(badgeid,))
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Removed player: %s %s' % (name, badgeid),))
            flash ('%s %s removed!' % (name, badgeid))
        db.commit()
        return redirect(url_for('add_player'))
    else:
        players = db.execute('SELECT name, badgeid, updated FROM players ORDER BY badgeid').fetchall()
        return render_template('add_player.html',players=players)

@app.route('/public_queue')
def public_queue():
    db = get_db()
    playing = db.execute('SELECT name, badgeid FROM players where status="playing" ORDER BY queue').fetchall()
    queued = db.execute('SELECT name, badgeid FROM players where status="queued" ORDER BY queue').fetchall()
    called = db.execute('SELECT name, badgeid FROM players where status="called" ORDER BY updated').fetchall()
    soon = db.execute('SELECT name, badgeid FROM players where status="inactive" ORDER BY updated LIMIT 10').fetchall()
    print(soon)
    return render_template('scoreboard.html', playing=playing, queued=queued, called=called, soon=soon,NAMES_PER_ROW=NAMES_PER_ROW)

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
        if command in ['forcecall','unkick']:
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Player unkicked/force called: %s %s' % (name, badgeid),))
            db.execute("UPDATE players SET status='called', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'queue':
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Placed in queue: %s %s' % (name, badgeid),))
            current_queue_no = db.execute("SELECT max(queue) from players WHERE status='queued' or status='playing';").fetchone()[0]
            if current_queue_no == None:
                current_queue_no = 1000
            else:
                current_queue_no += 1000
            db.execute("UPDATE players SET queue=?, status='queued', updated=datetime('now','localtime') \
                WHERE badgeid=?;",(current_queue_no,badgeid))
        elif command == 'kick':
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Player kicked: %s %s' % (name, badgeid),))
            db.execute("UPDATE players SET status='kicked', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'topofqueue':
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Move to top of queue: %s %s' % (name, badgeid),))
            (current_queue_no,topid) = db.execute("SELECT min(queue),badgeid from players WHERE status='queued';").fetchall()[0]
            if topid != badgeid:
                db.execute("UPDATE players SET queue=?, updated=datetime('now','localtime') \
                    WHERE badgeid=?;",(current_queue_no-1,badgeid))
        elif command == 'finish':
            score = int(request.args.get('score'))
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Score update: %s %s got %s points' % (name, badgeid, score),))
            db.execute("UPDATE players SET status='finished', score=?, updated=datetime('now','localtime') WHERE badgeid=?;",(score,badgeid))
        else:
            db.execute("INSERT INTO updates (message) VALUES (?)", ('not implemented: command %s on player %s' % (command, badgeid),))
            #flash('not implemented: command %s on player %s' % (command, badgeid))
        start_playing()
        fill_queue()
        db.commit()
        return redirect(url_for('admin_queue'))

    else:
        player_data_temp = db.execute("SELECT * FROM players WHERE status<>'kicked' AND status<>'finished' ORDER BY queue,ticket").fetchall()
        player_data_temp = [list(x) for x in player_data_temp]
        player_data = []
        for data in player_data_temp:
            thyme = datetime.datetime.strptime(data[6],'%Y-%m-%d %H:%M:%S') 
            delta = datetime.datetime.now() - thyme
            if delta.seconds > LATE_TIME:
                data.append('late')
            elif delta.seconds > WARN_TIME:
                data.append('warn')
            else:
                data.append('okay')
            player_data.append(data)
        print(player_data)
        kicked = db.execute("SELECT * FROM players WHERE status='kicked' ORDER BY badgeid").fetchall()
        finished = db.execute("SELECT * FROM players WHERE status='finished' ORDER BY score DESC").fetchall()
        messages = db.execute("SELECT * FROM updates ORDER BY update_time DESC LIMIT 10")
        return render_template('admin_queue.html',player_data=player_data,kicked=kicked,finished=finished,messages=messages)

@app.route('/score_queue')
def score_queue():
    db = get_db()
    command = request.args.get('command')
    if command != None:
        badgeid = int(request.args.get('id'))
        name = db.execute("SELECT name FROM players where badgeid=?",(badgeid,)).fetchone()[0]
        if command == 'finish':
            score = int(request.args.get('score'))
            db.execute("INSERT INTO updates (message) VALUES (?)", ('Score update: %s %s got %s points' % (name, badgeid, score),))
            db.execute("UPDATE players SET status='finished', score=?, updated=datetime('now','localtime') WHERE badgeid=?;",(score,badgeid))
        else:
            db.execute("INSERT INTO updates (message) VALUES (?)", ('not implemented: command %s on player %s' % (command, badgeid),))
        start_playing()
        fill_queue()
        db.commit()
        return redirect(url_for('score_queue'))

    else:
        player_data = db.execute("SELECT * FROM players WHERE status<>'kicked' AND status<>'finished' ORDER BY queue,ticket").fetchall()
        kicked = db.execute("SELECT * FROM players WHERE status='kicked' ORDER BY badgeid").fetchall()
        finished = db.execute("SELECT * FROM players WHERE status='finished' ORDER BY score DESC").fetchall()
        return render_template('score_queue.html',player_data=player_data,kicked=kicked,finished=finished)

@app.route('/fillqueue')
def manual_fill_queue():
    fill_queue()
    return 'filled!'

@app.route('/generate')
def generate():
    generate_players()
    fill_queue()
    return redirect(url_for('admin_queue'))


def fill_queue():
    db = get_db()
    queued_ids = db.execute("SELECT badgeid FROM players WHERE status='called' OR status='queued';").fetchall()
    waiting_ids = db.execute("SELECT badgeid FROM players WHERE status='inactive';").fetchall()
    number_to_queue = min([PEOPLE_IN_QUEUE-len(queued_ids), len(waiting_ids)])
    for i in range(number_to_queue):
        new_in_queue = db.execute("SELECT name, badgeid, min(ticket) FROM players WHERE status='inactive'").fetchone()
        name, newid, queue_no = new_in_queue
        db.execute("INSERT INTO updates (message) VALUES (?)", ('Called to queue: %s %s' % (name, newid),))
        #flash('Called to queue: %s %s' % (name, newid))
        db.execute("UPDATE players SET status='called', updated=datetime('now','localtime') \
            WHERE ticket=(SELECT min(ticket) FROM players WHERE status='inactive') ;")
    db.commit()

def start_playing():
    db = get_db()
    playing_ids = db.execute("SELECT badgeid FROM players WHERE status='playing';").fetchall()
    queued_ids = db.execute("SELECT badgeid FROM players WHERE status='queued';").fetchall()
    number_to_play = min([PEOPLE_PLAYING-len(playing_ids), len(queued_ids)])
    for i in range(number_to_play):
        new_player = db.execute("SELECT name, badgeid, min(queue) FROM players WHERE status='queued'").fetchone()
        name, newid, queue_no = new_player
        print(type(newid))
        db.execute("INSERT INTO updates (message) VALUES (?)", ('Now playing: %s %s' % (name, newid),))
        #flash('Now playing: %s %s' % (name, newid))
        db.execute("UPDATE players SET status='playing', updated=datetime('now','localtime') \
            WHERE badgeid=?;",(newid,))
    db.commit()

if __name__ == '__main__':
    app.run(host= '0.0.0.0')
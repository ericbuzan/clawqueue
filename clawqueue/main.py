# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, \
    url_for, abort, render_template, flash
from random import randint
from shutil import copy
from time import strftime
from generate_players import generate as generate_players

app = Flask(__name__) # create the application instance :)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'players.db'),
    SECRET_KEY='Sunny is a very nice kitty.',
    DEBUG = True
))

PEOPLE_IN_QUEUE = 5
PEOPLE_PLAYING = 3

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

@app.route('/queue')
def queue():
    db = get_db()
    command = request.args.get('do')
    if command != None:
        command, badgeid = command.split('_')
        badgeid = int(badgeid)
        print("command %s on player %s" % (command, badgeid))
        if command in ['forcecall','unkick']:
            db.execute("UPDATE players SET status='called', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'queue':
            current_queue_no = db.execute("SELECT max(queue) from players WHERE status='queued' or status='playing';").fetchone()[0]
            if current_queue_no == None:
                current_queue_no = 1
            else:
                current_queue_no += 1
            db.execute("UPDATE players SET queue=?, status='queued', updated=datetime('now','localtime') \
                WHERE badgeid=?;",(current_queue_no,badgeid))
        elif command == 'kick':
            db.execute("UPDATE players SET status='kicked', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        elif command == 'topofqueue':
            (current_queue_no,topid) = db.execute("SELECT min(queue),badgeid from players WHERE status='queued';").fetchall()[0]
            if topid != badgeid:
                db.execute("UPDATE players SET queue=?, updated=datetime('now','localtime') \
                    WHERE badgeid=?;",(current_queue_no-.001,badgeid))
        elif command == 'finish':
            db.execute("UPDATE players SET status='finished', updated=datetime('now','localtime') WHERE badgeid=?;",(badgeid,))
        else:
            flash('not implemented: command %s on player %s' % (command, badgeid))
        start_playing()
        fill_queue()
        db.commit()
        return redirect(url_for('queue'))

    else:
        player_data = db.execute("SELECT * FROM players WHERE status<>'kicked' AND status<>'finished' ORDER BY queue,ticket").fetchall()
        kicked = db.execute("SELECT * FROM players WHERE status='kicked' ORDER BY badgeid").fetchall()
        finished = db.execute("SELECT * FROM players WHERE status='finished' ORDER BY queue").fetchall()
        return render_template('queue.html',player_data=player_data,kicked=kicked,finished=finished)

@app.route('/fillqueue')
def manual_fill_queue():
    fill_queue()
    return 'filled!'

@app.route('/generate')
def generate():
    generate_players()
    fill_queue()
    return redirect(url_for('queue'))


def fill_queue():
    db = get_db()
    queued_ids = db.execute("SELECT badgeid FROM players WHERE status='called' OR status='queued';").fetchall()
    waiting_ids = db.execute("SELECT badgeid FROM players WHERE status='inactive';").fetchall()
    number_to_queue = min([PEOPLE_IN_QUEUE-len(queued_ids), len(waiting_ids)])
    for i in range(number_to_queue):
        new_in_queue = db.execute("SELECT name, badgeid, min(ticket) FROM players WHERE status='inactive'").fetchone()
        name, newid, queue_no = new_in_queue
        flash('Called to queue: %s %s' % (name, newid))
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
        flash('Now playing: %s %s' % (name, newid))
        db.execute("UPDATE players SET status='playing', updated=datetime('now','localtime') \
            WHERE badgeid=?;",(newid,))
    db.commit()

if __name__ == '__main__':
    app.run(host= '0.0.0.0')
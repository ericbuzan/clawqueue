drop table if exists players;

create table players (
  qid integer primary key autoincrement,
  name text not null,
  badgeid integer not null,
  status text default 'inactive',
  score integer default 0,
  updated datetime default (datetime('now','localtime'))
);

drop table if exists updates;

create table updates (
  update_time datetime default (datetime('now','localtime')),
  message text
);
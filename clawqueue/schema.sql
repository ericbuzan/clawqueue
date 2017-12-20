drop table if exists players;

create table players (
  ticket integer primary key autoincrement,
  queue real default 9999,
  name text not null,
  badgeid integer not null,
  status text default 'inactive',
  score integer default 0,
  updated datetime default (datetime('now','localtime'))
);
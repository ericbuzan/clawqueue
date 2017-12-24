drop table if exists players;

create table players (
  ticket integer primary key autoincrement,
  queue integer default 9999999,
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
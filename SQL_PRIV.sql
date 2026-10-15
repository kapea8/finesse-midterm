SELECT User, Host
FROM mysql.user
where user = 'FINESSE-USR'; 

select current_user(), user();


alter user 'root'@'localhost'
identified	by 'bc1hw1Tjp1X';
grant all privileges on ml_metrics.*
to 'root'@'localhost';

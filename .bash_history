id
source ./.venv/bin/activate
pip install psycopg2
exit
ls -a
python3 -m venv .venv
ls -a
source ./.venv/bin/activate
pip install django
django-admin startproject core source
cd source/
python manage.py runserver
clear
id
pip install psycopg2
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
pip install gunicorn
gunicorn core.wsgi:application --bind localhost:8001
tree
cd ..
ls
tree
sudo chmod U+x gunicorn_start 
sudo chmod u+x gunicorn_start 
ls -a
./gunicorn_start
sudo chmod +x gunicorn_start 
./gunicorn_start
tree -a
tree -L2 -a
tree -L 2 -a
./gunicorn_start
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl reread
sudo supervisorctl status geld
sudo supervisorctl restart geld
git status
pip freeze >> requirements.txt
pip install -r requirements.txt 
pip install python-dotenv
ls
cd source/
python manage.py runserver
python manage.py runserver
python manage.py runserver
git status
python manage.py startapp inventory
ls -a
cd ..
tree -a
tree -a -L 5

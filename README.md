# Geld
Homegrown accounting and invoicing software

# Development

Geld is intended to be run on a standalone Debian/Ubuntu system, using nginx and gunicorn as the production web proxy
and server setup. At some point it might be practical to dockerize everything but the priority was first to establish
a secure and robust production-like environment.

## Getting Started

### 1. Clone the repository into `/opt/` 
```bash
$ cd /opt/
$ git clone https://github.com/AlsoNotBen/geld.git
$ cd ./geld
```

### 2. Create a user `geld` and give it ownership or full permissions to the `/opt/geld/` directory.
```bash
$ sudo groupadd --system geld
$ sudo useradd --system --gid geld --shell /bin/bash --home /opt/geld geld
$ sudo su - geld
```

### 3. Create a virtual environment and install all requirements
```bash
$ python -m venv .venv
$ source ./.venv/bin/activate
(.venv)$ pip install -r requirements.txt
```

If you encounter any issues, there is a great tutorial by Michal Karzynski on setting up and running this Django/Nginx/Gunicorn stack, it is very similar to this setup but instead of using `hello`, use `geld` and use `/opt/geld` as your project root directory.  <br>

https://michal.karzynski.pl/blog/2013/06/09/django-nginx-gunicorn-virtualenv-supervisor/


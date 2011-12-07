run:
	./env/bin/python ./scripts/server kottapalli.yml

fcgi:
	./env/bin/python ./scripts/server kottapalli.yml startserver fastcgi 7011

venv:
	virtualenv --no-site-packages env
	./env/bin/pip install -r requirements.txt

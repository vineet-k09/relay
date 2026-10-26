db:
	sqlite3 .metasync.db
run:
	python ./main.py
reset:
	rm -rf .metasync.db
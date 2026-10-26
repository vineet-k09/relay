db:
	sqlite3 .relay.db
run:
	python ./main.py
reset:
	rm -rf .relay.db
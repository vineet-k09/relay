db:
	sqlite3 .relay.db
run:
	uv run relay
reset:
	rm -rf .relay.db
start:
	uv run main.py

test-mini:
	uv run test/mini.py

test-hasanah:
	uv run test/hasanah_card.py

deploy:
	docker compose up --build

down:
	docker compose down

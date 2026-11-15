.PHONY: verify test test-integration
verify:
	python3 scripts/check-source.py
	python3 -m unittest discover -s scripts -p 'test_*.py'
	cd backend && test -z "$$(gofmt -l cmd internal)" && go vet ./... && go test -race ./... && go build ./cmd/dedhed
	pnpm --dir web install --frozen-lockfile
	pnpm --dir web typecheck
	pnpm --dir web lint
	pnpm --dir web test
	pnpm --dir web build
test:
	cd backend && go test -race ./...
	pnpm --dir web test
test-integration:
	test -n "$(TEST_DATABASE_URL)"
	cd backend && go test -race ./internal/catalog -count=1

.PHONY: verify-core-pin
verify: verify-core-pin
verify-core-pin: ## Verify the independent Arkhiv engine receipt and deployment recipe
	python3 scripts/check_core_pin.py
	CORE_SUBNET=10.254.70.0/24 DERIVATIVE_ROOT=/tmp/arkhiv-derivatives docker compose --env-file deploy/archive-core.env -f deploy/core-compose.yml config --quiet

.PHONY: verify-viewer-pin
verify: verify-viewer-pin
verify-viewer-pin:
	python3 scripts/check_viewer_pin.py

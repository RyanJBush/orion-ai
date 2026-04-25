# Contributing

## Development

1. Run `make setup` (or `make install`) to install backend and frontend dependencies.
2. Run `make dev-backend` for the API service.
3. In another terminal, run `make dev-frontend` for the UI.
4. Run `make test && make lint` before opening updates.
5. Optional demo-prep check: seed templates with `POST /api/v1/workflows/templates/seed-demo` and run one template end-to-end.

## Environment configuration

- Copy `backend/.env.example` to `backend/.env` and update secrets/connection strings as needed.

## Commit style

- Keep PRs focused and small.
- Add/update tests with behavioral changes.

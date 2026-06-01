# brewspace frontend component

This component serves a static HTML/JavaScript page over NGINX.

The page calls `/health` on the API and renders:

- `API Status: OK` when the API returns `{ "status": "ok" }`

On the cluster, NGINX proxies `/health` to the `brewspace-api` Service (same namespace).

For local static hosting without that proxy, open the page with `?api=http://127.0.0.1:8080` while the API listens on port 8080.

## Build context

- Source path: `applications/brewspace/components/frontend`
- Containerfile: `applications/brewspace/components/frontend/Containerfile`

# ── Stage 1: Development ──────────────────────────────────────────────────────
# Used by docker-compose.yml (default).
# Source code is bind-mounted at runtime; node_modules lives in a named volume
# so the container's modules are isolated from the host filesystem.
FROM node:20-alpine AS development

WORKDIR /app

# Install dependencies first so this layer is cached independently of source changes
COPY package.json package-lock.json* ./
RUN npm install

EXPOSE 5173

# Vite's vite.config.ts already sets host: '0.0.0.0' — no flag needed
CMD ["npm", "run", "dev"]


# ── Stage 2: Builder ──────────────────────────────────────────────────────────
# Compiles the production bundle. Output lands in /app/dist.
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build


# ── Stage 3: Production ───────────────────────────────────────────────────────
# Minimal nginx image serving the static bundle and proxying /api/ to the backend.
# No Node.js runtime in this image — just nginx and static files.
FROM nginx:1.27-alpine AS production

# Remove nginx's default config
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx runs as the built-in 'nginx' user (UID 101) by default in this image

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

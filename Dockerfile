# FunPod — RunPod Gaming Launcher
# Electron + React + Tailwind — GOLD Tier
FROM node:20-slim AS build

WORKDIR /app
COPY funpod-v2/package*.json ./funpod-v2/
RUN cd funpod-v2 && npm ci
COPY funpod-v2/ ./funpod-v2/
RUN cd funpod-v2 && npx vite build

# Runtime
FROM node:20-slim
WORKDIR /app
COPY --from=build /app/funpod-v2/dist ./dist
COPY --from=build /app/funpod-v2/dist-electron ./dist-electron
COPY --from=build /app/funpod-v2/package.json .
COPY --from=build /app/funpod-v2/node_modules ./node_modules

EXPOSE 5173
CMD ["npx", "vite", "preview", "--host", "0.0.0.0"]

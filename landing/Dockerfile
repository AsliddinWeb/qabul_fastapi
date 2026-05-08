# syntax=docker/dockerfile:1.6

# ============ deps ============
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps

# ============ dev ============
FROM deps AS dev
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# ============ build ============
FROM deps AS build
COPY . .
RUN npm run build

# ============ prod ============
FROM node:20-alpine AS prod
WORKDIR /app
ENV NODE_ENV=production \
    NUXT_HOST=0.0.0.0 \
    NUXT_PORT=3000
COPY --from=build /app/.output ./.output
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]

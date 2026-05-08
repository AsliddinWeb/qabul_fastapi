# syntax=docker/dockerfile:1.6

# ============ base ============
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps

# ============ dev ============
FROM base AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ============ build ============
FROM base AS build
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_APP_NAME="XIU Qabul"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_APP_NAME=${VITE_APP_NAME}
COPY . .
RUN npm run build

# ============ prod (nginx static) ============
FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

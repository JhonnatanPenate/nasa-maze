FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_MARS_TILE_URL=
ENV VITE_MARS_TILE_URL=$VITE_MARS_TILE_URL
RUN npm run build

FROM nginx:1.27-alpine
ENV CORE_UPSTREAM=http://core:8000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# The browser talks to the backend directly (CORS is open). At image-build
# time we bake in the URL the browser will use to reach the backend container.
ARG VITE_API_BASE="http://localhost:8000"
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

EXPOSE 5173
# Serve the built static bundle.
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]

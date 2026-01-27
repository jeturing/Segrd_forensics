# Base image
FROM node:18-alpine as build

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy source code and build the app
COPY . .
RUN npm run build

# Serve the app using a lightweight web server
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
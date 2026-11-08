FROM node:20-alpine

WORKDIR /app

# Instalar dependencias de Node primero para aprovechar caché de capas Docker
COPY package.json ./
RUN npm install

# Copiar código fuente del frontend
COPY . .

EXPOSE 5173

# Levantar Vite exponiendo hacia afuera del contenedor
CMD ["npm", "run", "dev"]

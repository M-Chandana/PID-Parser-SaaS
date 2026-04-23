FROM node:20-slim

WORKDIR /app

# Install system dependencies (openssl is often needed for Prisma)
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Generate Prisma client
RUN npx prisma generate

# Expose API port
EXPOSE 5000

# Default command (can be overridden to run worker)
CMD ["node", "src/index.js"]

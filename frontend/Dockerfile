FROM node:18-alpine

# Set working directory
WORKDIR /app

# Set environment variables
ENV PATH /app/node_modules/.bin:$PATH

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install --silent

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Start development server
CMD ["npm", "start"]

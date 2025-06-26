#!/usr/bin/env python3
"""
Script para extrair as rotas web e criar a estrutura do frontend separado
"""

import os
import json
import shutil
from datetime import datetime

def create_frontend_structure():
    """Cria a estrutura básica do projeto frontend"""
    
    base_dir = "/tmp/videoai-web"
    
    # Criar estrutura de diretórios
    directories = [
        "src/components",
        "src/pages", 
        "src/services",
        "src/assets/css",
        "src/assets/js",
        "src/assets/img",
        "public",
        "docs"
    ]
    
    for directory in directories:
        os.makedirs(f"{base_dir}/{directory}", exist_ok=True)
    
    # 1. Package.json
    package_json = {
        "name": "videoai-web",
        "version": "1.0.0",
        "description": "VideoAI Web Interface - Frontend para consumir VideoAI API",
        "main": "src/index.js",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview",
            "start": "npm run dev"
        },
        "dependencies": {
            "vue": "^3.4.0",
            "vue-router": "^4.2.0",
            "axios": "^1.6.0",
            "bootstrap": "^5.3.0",
            "@fortawesome/fontawesome-free": "^6.5.0"
        },
        "devDependencies": {
            "@vitejs/plugin-vue": "^4.5.0",
            "vite": "^5.0.0"
        },
        "keywords": ["videoai", "subtitles", "video", "transcription", "vue"],
        "author": "GestorLead",
        "license": "MIT"
    }
    
    with open(f"{base_dir}/package.json", 'w') as f:
        json.dump(package_json, f, indent=2)
    
    # 2. Vite config
    vite_config = '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})'''
    
    with open(f"{base_dir}/vite.config.js", 'w') as f:
        f.write(vite_config)
    
    # 3. Index.html
    index_html = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VideoAI - Geração Automática de Legendas</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
</body>
</html>'''
    
    with open(f"{base_dir}/index.html", 'w') as f:
        f.write(index_html)
    
    # 4. Main.js
    main_js = '''import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import apiService from './services/api.js'

// Páginas
import Home from './pages/Home.vue'
import Login from './pages/Login.vue'
import Dashboard from './pages/Dashboard.vue'
import VideoDetail from './pages/VideoDetail.vue'
import Upload from './pages/Upload.vue'
import Profile from './pages/Profile.vue'
import Settings from './pages/Settings.vue'

// Configurar rotas
const routes = [
    { path: '/', component: Home },
    { path: '/login', component: Login },
    { path: '/dashboard', component: Dashboard, meta: { requiresAuth: true } },
    { path: '/video/:id', component: VideoDetail, meta: { requiresAuth: true } },
    { path: '/upload', component: Upload, meta: { requiresAuth: true } },
    { path: '/profile', component: Profile, meta: { requiresAuth: true } },
    { path: '/settings', component: Settings, meta: { requiresAuth: true } }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// Guard de autenticação
router.beforeEach((to, from, next) => {
    if (to.matched.some(record => record.meta.requiresAuth)) {
        if (!apiService.isAuthenticated()) {
            next('/login')
        } else {
            next()
        }
    } else {
        next()
    }
})

const app = createApp(App)
app.use(router)
app.mount('#app')'''
    
    with open(f"{base_dir}/src/main.js", 'w') as f:
        f.write(main_js)
    
    # 5. App.vue
    app_vue = '''<template>
  <div id="app">
    <Navbar />
    <div class="container mt-4">
      <router-view />
    </div>
    <Footer />
  </div>
</template>

<script>
import Navbar from './components/Navbar.vue'
import Footer from './components/Footer.vue'

export default {
  name: 'App',
  components: {
    Navbar,
    Footer
  }
}
</script>

<style>
/* Estilos globais */
</style>'''
    
    with open(f"{base_dir}/src/App.vue", 'w') as f:
        f.write(app_vue)
    
    # 6. Serviço da API
    api_service = '''const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1'

class ApiService {
    constructor() {
        this.token = localStorage.getItem('auth_token')
    }

    getHeaders() {
        const headers = {
            'Content-Type': 'application/json'
        }
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`
        }
        
        return headers
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(),
                ...options.headers
            }
        }

        const response = await fetch(url, config)
        
        if (response.status === 401) {
            this.logout()
            window.location.href = '/login'
            return
        }

        return response
    }

    // Autenticação
    async login(username, password) {
        const response = await this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        })
        
        if (response.ok) {
            const data = await response.json()
            this.token = data.token
            localStorage.setItem('auth_token', this.token)
            return data
        }
        
        throw new Error('Login falhou')
    }

    logout() {
        this.token = null
        localStorage.removeItem('auth_token')
    }

    isAuthenticated() {
        return !!this.token
    }

    // Vídeos
    async getVideos() {
        const response = await this.request('/videos')
        return response.json()
    }

    async getVideo(id) {
        const response = await this.request(`/videos/${id}`)
        return response.json()
    }

    async uploadVideo(formData) {
        const response = await this.request('/video/process', {
            method: 'POST',
            body: formData
        })
        return response.json()
    }

    // Legendas
    async getSubtitles(videoId) {
        const response = await this.request(`/videos/${videoId}/subtitles`)
        return response.json()
    }

    async downloadSubtitle(subtitleId) {
        const response = await this.request(`/subtitles/${subtitleId}/download`)
        return response.blob()
    }
}

export default new ApiService()'''
    
    with open(f"{base_dir}/src/services/api.js", 'w') as f:
        f.write(api_service)
    
    # 7. Dockerfile
    dockerfile = '''FROM node:18-alpine

WORKDIR /app

# Copiar package files
COPY package*.json ./

# Instalar dependências
RUN npm install

# Copiar código
COPY . .

# Build da aplicação
RUN npm run build

# Servir aplicação
FROM nginx:alpine
COPY --from=0 /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]'''
    
    with open(f"{base_dir}/Dockerfile", 'w') as f:
        f.write(dockerfile)
    
    # 8. Docker Compose
    docker_compose = '''version: '3.8'

services:
  web:
    build: .
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:5000/api/v1
    depends_on:
      - api
  
  api:
    image: gestorlead/videoai-api:latest
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/videoai
      - CORS_ORIGINS=http://localhost:3000,https://videoai.com
    depends_on:
      - db
      - redis
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=videoai
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:alpine

volumes:
  postgres_data:'''
    
    with open(f"{base_dir}/docker-compose.yml", 'w') as f:
        f.write(docker_compose)
    
    # 9. README
    readme = f'''# VideoAI Web

Interface web moderna para o VideoAI API.

## 🚀 Tecnologias

- Vue.js 3
- Vue Router
- Bootstrap 5
- Vite
- Docker

## 🛠️ Desenvolvimento

```bash
# Instalar dependências
npm install

# Servidor de desenvolvimento
npm run dev

# Build para produção
npm run build
```

## 🔧 Configuração

Configurar a URL da API no arquivo `.env`:

```
VITE_API_URL=http://localhost:5000/api/v1
```

## 📦 Docker

```bash
# Build da imagem
docker build -t videoai-web .

# Executar com docker-compose
docker-compose up -d
```

## 🔗 Endpoints da API

A aplicação consome os seguintes endpoints:

- `GET /api/v1/videos` - Listar vídeos
- `POST /api/v1/video/process` - Upload de vídeo
- `GET /api/v1/videos/{{id}}` - Detalhes do vídeo
- `GET /api/v1/subtitles/{{id}}/download` - Download de legenda

## 📄 Estrutura

```
src/
├── components/     # Componentes reutilizáveis
├── pages/         # Páginas da aplicação
├── services/      # Serviços da API
└── assets/        # CSS, JS, imagens
```

---

Gerado automaticamente em {datetime.now().strftime('%d/%m/%Y %H:%M')}
'''
    
    with open(f"{base_dir}/README.md", 'w') as f:
        f.write(readme)
    
    print(f"✅ Estrutura do frontend criada em: {base_dir}")
    print(f"📁 Diretórios criados: {len(directories)}")
    print(f"📄 Arquivos base criados: 9")
    
    return base_dir

if __name__ == "__main__":
    create_frontend_structure() 
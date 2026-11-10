import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backend = `http://127.0.0.1:${process.env.BUILDSEC_BACKEND_PORT || '8000'}`
export default defineConfig({ plugins: [react()], server: { proxy: { '/executions': backend, '/runtime': backend } } })

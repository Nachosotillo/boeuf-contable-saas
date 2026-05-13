import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 3500,
          style: {
            fontFamily: '"DM Sans", sans-serif',
            fontSize: '13px',
            borderRadius: '10px',
            border: '0.5px solid #e2e8f0',
            boxShadow: '0 4px 12px rgb(0 0 0 / 0.1)',
          },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
)

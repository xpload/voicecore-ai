# VoiceCore AI 2.0 Frontend

Modern React 18 + TypeScript frontend for VoiceCore AI 2.0 enterprise virtual receptionist platform.

## Technology Stack

- **React 18** - Latest React with concurrent features
- **TypeScript 5** - Strict type safety
- **Material-UI (MUI)** - Component library and design system
- **Zustand** - Lightweight state management
- **React Query** - Server state management
- **Socket.io** - Real-time WebSocket communication
- **Axios** - HTTP client
- **Recharts** - Data visualization
- **Framer Motion** - Animations
- **React Router** - Client-side routing

## Project Structure

```
src/
├── components/     # React components
├── hooks/          # Custom React hooks
├── services/       # API and external services
├── store/          # Zustand state management
├── types/          # TypeScript type definitions
├── utils/          # Utility functions
├── App.tsx         # Main application component
└── index.tsx       # Application entry point
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on http://localhost:8000

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm start
```

Runs the app in development mode at [http://localhost:3000](http://localhost:3000).

### Build

```bash
npm run build
```

Builds the app for production to the `build` folder.

### Environment Variables

Create a `.env` file in the frontend directory:

```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=http://localhost:8000
```

## Features

- ✅ React 18 with TypeScript
- ✅ Strict TypeScript configuration
- ✅ ESLint and Prettier setup
- ✅ Material-UI design system
- ✅ Zustand state management
- ✅ API service layer
- ✅ WebSocket integration
- ✅ Responsive navigation
- ✅ Theme support (light/dark)
- 🚧 Dashboard customization
- 🚧 Real-time updates
- 🚧 Data visualizations
- 🚧 PWA capabilities

## Code Style

- Use functional components with hooks
- Follow TypeScript strict mode
- Use path aliases (@components, @hooks, etc.)
- Keep components small and focused
- Write self-documenting code with clear names

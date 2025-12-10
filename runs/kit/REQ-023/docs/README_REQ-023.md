# REQ-023: Frontend Campaign Management UI

## Quick Start

### Prerequisites

- Node.js 20+
- npm or yarn

### Installation

bash
cd runs/kit/REQ-023/src/frontend
npm install

### Development

bash
npm run dev

The application will be available at http://localhost:3000

### Testing

bash
npm test

### Building

bash
npm run build

### Type Checking

bash
npm run type-check

### Linting

bash
npm run lint

## Project Structure

src/frontend/
├── src/
│   ├── app/           # Next.js pages
│   ├── components/    # React components
│   ├── lib/           # Utilities and API
│   ├── store/         # State management
│   └── types/         # TypeScript types
├── test/              # Test files
└── package.json

## Environment Variables

Create a `.env.local` file:

env
NEXT_PUBLIC_API_URL=http://localhost:8000

## API Integration

The frontend expects the backend API to be running at the configured URL. Ensure REQ-004 and REQ-006 backend services are available.

## Features

- Campaign list with filtering and pagination
- Campaign creation and editing
- CSV contact upload with drag-drop
- Campaign activation/pause controls
- Form validation
- Responsive design
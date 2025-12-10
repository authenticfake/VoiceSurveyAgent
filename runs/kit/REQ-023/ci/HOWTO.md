# HOWTO: REQ-023 Frontend Campaign Management UI

## Prerequisites

- Node.js 20+ installed
- npm 10+ installed
- Backend API running (REQ-004, REQ-006)

## Environment Setup

### 1. Install Node.js

bash
# Using nvm (recommended)
nvm install 20
nvm use 20

# Verify installation
node --version  # Should be v20.x.x
npm --version   # Should be v10.x.x

### 2. Install Dependencies

bash
cd runs/kit/REQ-023/src/frontend
npm ci

### 3. Configure Environment

Create `.env.local`:
bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

## Running Tests

### All Tests
bash
npm test

### With Coverage
bash
npm test -- --coverage

### Watch Mode
bash
npm test -- --watch

### Specific Test File
bash
npm test -- --testPathPattern=campaign-list

## Running the Application

### Development Mode
bash
npm run dev

Access at http://localhost:3000

### Production Build
bash
npm run build
npm start

## Code Quality

### Type Checking
bash
npm run type-check

### Linting
bash
npm run lint
npm run lint:fix  # Auto-fix issues

## CI/CD Integration

### GitHub Actions
The LTC.json defines the CI pipeline:
1. Install dependencies
2. Type check
3. Lint
4. Run tests with coverage
5. Build

### Running CI Locally
bash
# Install
npm ci

# Type check
npm run type-check

# Lint
npm run lint

# Test
npm test -- --coverage --passWithNoTests

# Build
npm run build

## Troubleshooting

### Common Issues

#### 1. Module Not Found
bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

#### 2. Type Errors
bash
# Check TypeScript version
npx tsc --version

# Run type check with verbose output
npm run type-check -- --verbose

#### 3. Test Failures
bash
# Run tests with verbose output
npm test -- --verbose

# Run single test file
npm test -- path/to/test.tsx

#### 4. Build Errors
bash
# Clear Next.js cache
rm -rf .next

# Rebuild
npm run build

### API Connection Issues

If the frontend cannot connect to the backend:

1. Verify backend is running:
bash
curl http://localhost:8000/api/campaigns

2. Check CORS configuration in backend

3. Verify environment variable:
bash
echo $NEXT_PUBLIC_API_URL

## Project Structure

runs/kit/REQ-023/
├── src/frontend/           # Frontend application
│   ├── src/
│   │   ├── app/           # Next.js pages
│   │   ├── components/    # React components
│   │   ├── lib/           # Utilities
│   │   ├── store/         # State management
│   │   └── types/         # TypeScript types
│   ├── package.json
│   └── tsconfig.json
├── test/                   # Test files
├── docs/                   # Documentation
└── ci/                     # CI configuration

## Dependencies

### Production
- next: Next.js framework
- react: UI library
- axios: HTTP client
- zustand: State management
- react-dropzone: File upload
- lucide-react: Icons
- tailwindcss: Styling

### Development
- jest: Testing framework
- @testing-library/react: React testing utilities
- typescript: Type checking
- eslint: Linting

---

## KIT Iteration Log

### Targeted REQ-ID(s)
- **REQ-023**: Frontend campaign management UI

### Rationale
REQ-023 is the next open REQ in the frontend track. It depends on REQ-004 (Campaign CRUD API) and REQ-006 (Contact CSV upload) which are both in_progress, meaning their backend APIs are available for integration.

### In Scope
- Campaign list page with status badges and filtering
- Campaign create/edit forms with validation
- CSV upload component with drag-drop and progress
- Campaign detail view with action buttons
- Responsive design for desktop and tablet
- State management with Zustand
- API client integration
- Unit tests for components and store

### Out of Scope
- Authentication UI (handled by REQ-002)
- Dashboard and export UI (REQ-024)
- Mobile-specific navigation
- Real-time updates via WebSocket

### How to Run Tests

bash
# Navigate to frontend directory
cd runs/kit/REQ-023/src/frontend

# Install dependencies
npm ci

# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- --testPathPattern=campaign-list

### Prerequisites
- Node.js 20+
- npm 10+
- Backend API running at http://localhost:8000 (for integration testing)

### Dependencies and Mocks
- **Mocked**: `useCampaignStore` in component tests to isolate component behavior
- **Mocked**: `next/navigation` for router functionality in tests
- **Mocked**: `@/lib/api/campaigns` in store tests to test store logic independently

### Product Owner Notes
- Form validation rules match backend validation from REQ-005
- CSV upload shows detailed error information for rejected rows
- Campaign activation requires passing validation first
- Non-draft campaigns have limited editing capabilities

### RAG Citations
- `runs/kit/REQ-004/src/app/campaigns/router.py` - Campaign API endpoints structure
- `runs/kit/REQ-006/src/app/contacts/service.py` - Contact upload service patterns
- `runs/kit/REQ-017/src/app/dashboard/schemas.py` - Schema patterns for API responses

json
{
  "index": [
    {
      "req": "REQ-023",
      "src": [
        "runs/kit/REQ-023/src/frontend/package.json",
        "runs/kit/REQ-023/src/frontend/src/app/",
        "runs/kit/REQ-023/src/frontend/src/components/",
        "runs/kit/REQ-023/src/frontend/src/lib/",
        "runs/kit/REQ-023/src/frontend/src/store/",
        "runs/kit/REQ-023/src/frontend/src/types/"
      ],
      "tests": [
        "runs/kit/REQ-023/test/components/",
        "runs/kit/REQ-023/test/lib/",
        "runs/kit/REQ-023/test/store/"
      ]
    }
  ]
}
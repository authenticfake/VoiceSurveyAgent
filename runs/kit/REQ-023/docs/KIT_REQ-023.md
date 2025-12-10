# KIT Documentation — REQ-023: Frontend Campaign Management UI

## Overview

This KIT implements the frontend campaign management UI for the VoiceSurveyAgent application. It provides a React/Next.js-based web interface for managing survey campaigns, including campaign creation, editing, CSV contact upload, and campaign lifecycle management.

## Acceptance Criteria Coverage

| Criterion | Implementation | Status |
|-----------|---------------|--------|
| Campaign list page shows all campaigns with status badges | `CampaignList` component with `StatusBadge` | ✅ |
| CSV upload component with drag-drop and progress indicator | `CSVUploadDropzone` with react-dropzone | ✅ |
| Activate button enabled only when validation passes | `CampaignDetail` validates before activation | ✅ |
| Form validation matches backend rules | `CampaignForm` with client-side validation | ✅ |
| Responsive design for desktop and tablet | Tailwind CSS responsive classes | ✅ |

## Architecture

### Component Structure

src/
├── app/                    # Next.js App Router pages
│   ├── campaigns/          # Campaign pages
│   │   ├── [id]/          # Campaign detail & edit
│   │   └── new/           # Create campaign
│   └── layout.tsx         # Root layout
├── components/
│   ├── campaigns/         # Campaign-specific components
│   │   ├── campaign-list.tsx
│   │   ├── campaign-form.tsx
│   │   ├── campaign-detail.tsx
│   │   └── csv-upload-dropzone.tsx
│   ├── layout/            # Layout components
│   │   ├── header.tsx
│   │   └── main-layout.tsx
│   └── ui/                # Reusable UI components
│       ├── button.tsx
│       ├── input.tsx
│       ├── select.tsx
│       ├── badge.tsx
│       └── ...
├── lib/
│   ├── api/               # API client and functions
│   │   ├── client.ts
│   │   └── campaigns.ts
│   └── utils.ts           # Utility functions
├── store/
│   └── campaign-store.ts  # Zustand state management
└── types/                 # TypeScript type definitions
    ├── campaign.ts
    └── contact.ts

### State Management

The application uses Zustand for state management with the following store structure:

- **Campaign List State**: campaigns, pagination, loading, errors
- **Campaign Detail State**: currentCampaign, loading, errors
- **Validation State**: validationResult, isValidating
- **Upload State**: uploadProgress, uploadResult

### API Integration

The frontend integrates with the backend APIs from REQ-004 and REQ-006:

- `GET /api/campaigns` - List campaigns with pagination and filtering
- `POST /api/campaigns` - Create new campaign
- `GET /api/campaigns/{id}` - Get campaign details
- `PUT /api/campaigns/{id}` - Update campaign
- `DELETE /api/campaigns/{id}` - Delete campaign
- `POST /api/campaigns/{id}/activate` - Activate campaign
- `POST /api/campaigns/{id}/pause` - Pause campaign
- `POST /api/campaigns/{id}/contacts/upload` - Upload contacts CSV

## Key Features

### Campaign List

- Paginated list view with status filtering
- Status badges with color coding
- Contact count display
- Quick navigation to campaign details

### Campaign Form

- Create and edit modes
- Client-side validation matching backend rules
- Question configuration (3 questions with type selection)
- Call settings (max attempts, retry interval, time window)
- Disabled fields for non-draft campaigns

### CSV Upload

- Drag-and-drop file selection
- Upload progress indicator
- Detailed error reporting for rejected rows
- Success/warning/error states

### Campaign Detail

- Full campaign information display
- Action buttons based on campaign status
- Validation before activation
- Delete confirmation modal

## Validation Rules

The form implements the following validation rules to match backend:

1. **Campaign Name**: Required, non-empty
2. **Max Attempts**: Must be between 1 and 5
3. **Retry Interval**: Must be at least 1 minute
4. **Time Window**: End time must be after start time

## Responsive Design

The UI is responsive using Tailwind CSS:

- **Desktop**: Full layout with sidebar navigation
- **Tablet**: Condensed layout with collapsible elements
- **Mobile**: Stack layout with hamburger menu (future enhancement)

## Dependencies

### Production
- next: 14.2.21
- react: ^18.3.1
- axios: ^1.7.9
- zustand: ^5.0.2
- react-dropzone: ^14.3.5
- lucide-react: ^0.468.0
- tailwindcss: ^3.4.17

### Development
- @testing-library/react: ^16.1.0
- jest: ^29.7.0
- typescript: ^5.7.2

## Testing

Tests are organized by component type:

- **UI Components**: Button, Input, Badge, etc.
- **Campaign Components**: List, Form, Detail, Upload
- **Store**: Zustand store actions and state
- **Utilities**: Helper functions

Run tests with:
bash
npm test

## Configuration

Environment variables:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)

## Future Enhancements

1. Mobile-responsive navigation menu
2. Real-time campaign status updates via WebSocket
3. Bulk campaign operations
4. Advanced filtering and search
5. Campaign templates
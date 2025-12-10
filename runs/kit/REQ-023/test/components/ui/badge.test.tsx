/**
 * Badge component tests.
 * REQ-023: Frontend campaign management UI
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { Badge, StatusBadge } from '@/components/ui/badge';

describe('Badge', () => {
  it('renders children correctly', () => {
    render(<Badge>Test Badge</Badge>);
    expect(screen.getByText('Test Badge')).toBeInTheDocument();
  });

  it('applies default variant styles', () => {
    render(<Badge>Default</Badge>);
    expect(screen.getByText('Default')).toHaveClass('bg-gray-100', 'text-gray-800');
  });

  it('applies success variant styles', () => {
    render(<Badge variant="success">Success</Badge>);
    expect(screen.getByText('Success')).toHaveClass('bg-green-100', 'text-green-800');
  });

  it('applies warning variant styles', () => {
    render(<Badge variant="warning">Warning</Badge>);
    expect(screen.getByText('Warning')).toHaveClass('bg-yellow-100', 'text-yellow-800');
  });

  it('applies error variant styles', () => {
    render(<Badge variant="error">Error</Badge>);
    expect(screen.getByText('Error')).toHaveClass('bg-red-100', 'text-red-800');
  });

  it('applies info variant styles', () => {
    render(<Badge variant="info">Info</Badge>);
    expect(screen.getByText('Info')).toHaveClass('bg-blue-100', 'text-blue-800');
  });
});

describe('StatusBadge', () => {
  it('renders draft status correctly', () => {
    render(<StatusBadge status="draft" />);
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('renders running status with success variant', () => {
    render(<StatusBadge status="running" />);
    const badge = screen.getByText('Running');
    expect(badge).toHaveClass('bg-green-100');
  });

  it('renders paused status with warning variant', () => {
    render(<StatusBadge status="paused" />);
    const badge = screen.getByText('Paused');
    expect(badge).toHaveClass('bg-yellow-100');
  });

  it('renders cancelled status with error variant', () => {
    render(<StatusBadge status="cancelled" />);
    const badge = screen.getByText('Cancelled');
    expect(badge).toHaveClass('bg-red-100');
  });

  it('renders scheduled status with info variant', () => {
    render(<StatusBadge status="scheduled" />);
    const badge = screen.getByText('Scheduled');
    expect(badge).toHaveClass('bg-blue-100');
  });
});
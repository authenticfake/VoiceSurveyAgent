/**
 * Test setup file.
 * REQ-024: Frontend dashboard and export UI
 */

import '@testing-library/jest-dom';

// Mock window.URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url');
global.URL.revokeObjectURL = jest.fn();

// Mock ResizeObserver
global.ResizeObserver = jest.fn().mockImplementation(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));
import "@testing-library/jest-dom/vitest";

beforeAll(() => {
  if (!window.URL.createObjectURL) {
    window.URL.createObjectURL = () => "blob:mock";
  }
  if (!window.URL.revokeObjectURL) {
    window.URL.revokeObjectURL = () => {};
  }
});

afterEach(() => {
  vi.restoreAllMocks();
});
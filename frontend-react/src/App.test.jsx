import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

describe('App', () => {
  it('should pass a basic test', () => {
    expect(true).toBe(true);
  });

  it('should render a div', () => {
    render(<div data-testid="test-div">Hello World</div>);
    expect(screen.getByTestId('test-div')).toBeInTheDocument();
  });
});

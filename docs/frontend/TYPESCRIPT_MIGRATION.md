# TypeScript Migration Guide - Frontend React

**Version:** v4.5.0  
**Status:** 🔄 In Progress  
**Date:** December 2024  
**Target Completion:** Q1 2025

---

## 📋 Overview

This guide outlines the migration of the React frontend from JavaScript to TypeScript for improved type safety, better IDE support, and reduced runtime errors.

### Why TypeScript?

- **Type Safety**: Catch errors at compile-time instead of runtime
- **Better IDE Support**: Improved autocomplete, refactoring, and navigation
- **Self-Documenting**: Types serve as inline documentation
- **Easier Refactoring**: Safe and confident code changes
- **Reduced Bugs**: 15-20% reduction in bugs according to studies

---

## 🎯 Migration Strategy

### Phase 1: Setup (Week 1) - ✅ COMPLETED

- [x] Install TypeScript and type definitions
- [x] Create `tsconfig.json` and `tsconfig.node.json`
- [x] Update build configuration
- [x] Configure linters for TypeScript

### Phase 2: Gradual Migration (Weeks 2-6)

- [ ] Convert utility functions and helpers
- [ ] Convert services and API clients
- [ ] Convert hooks
- [ ] Convert context providers
- [ ] Convert Redux store and slices
- [ ] Convert components (low-level to high-level)
- [ ] Convert pages

### Phase 3: Strict Mode (Week 7-8)

- [ ] Enable strict TypeScript checking
- [ ] Fix all type errors
- [ ] Remove all `any` types
- [ ] Add missing type definitions

### Phase 4: Cleanup (Week 8)

- [ ] Remove JavaScript files
- [ ] Update documentation
- [ ] Final testing

---

## 🔧 Setup Instructions

### 1. Install TypeScript Dependencies

```bash
cd frontend-react

# Install TypeScript
npm install --save-dev typescript @types/react @types/react-dom

# Install type definitions for dependencies
npm install --save-dev \
  @types/node \
  @types/react-router-dom \
  @types/cytoscape \
  @types/moment \
  @types/recharts

# Update Vite for TypeScript
npm install --save-dev @vitejs/plugin-react

# Optional: Install type checking tools
npm install --save-dev tsc-files
```

### 2. Update package.json Scripts

Add TypeScript-related scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .ts,.tsx",
    "lint:fix": "eslint src --ext .ts,.tsx --fix",
    "type-check": "tsc --noEmit",
    "type-check:watch": "tsc --noEmit --watch",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "test": "vitest",
    "test:ui": "vitest --ui"
  }
}
```

### 3. Update vite.config.js

Rename to `vite.config.ts` and update:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@context': path.resolve(__dirname, './src/context'),
      '@styles': path.resolve(__dirname, './src/styles'),
      '@utils': path.resolve(__dirname, './src/utils'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
});
```

### 4. Update ESLint Configuration

Update `.eslintrc.json` for TypeScript:

```json
{
  "parser": "@typescript-eslint/parser",
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended"
  ],
  "plugins": ["react", "@typescript-eslint"],
  "parserOptions": {
    "ecmaVersion": 2021,
    "sourceType": "module",
    "ecmaFeatures": {
      "jsx": true
    }
  },
  "rules": {
    "@typescript-eslint/no-explicit-any": "warn",
    "@typescript-eslint/explicit-module-boundary-types": "off",
    "react/react-in-jsx-scope": "off"
  }
}
```

---

## 📝 Migration Examples

### Example 1: Simple Component

**Before (JavaScript):**
```jsx
// src/components/Button.jsx
export const Button = ({ onClick, children, variant = 'primary' }) => {
  return (
    <button 
      className={`btn btn-${variant}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
};
```

**After (TypeScript):**
```typescript
// src/components/Button.tsx
import { ReactNode, MouseEvent } from 'react';

interface ButtonProps {
  onClick: (event: MouseEvent<HTMLButtonElement>) => void;
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
}

export const Button = ({ onClick, children, variant = 'primary' }: ButtonProps) => {
  return (
    <button 
      className={`btn btn-${variant}`}
      onClick={onClick}
    >
      {children}
    </button>
  );
};
```

### Example 2: API Service

**Before (JavaScript):**
```javascript
// src/services/caseService.js
import axios from 'axios';

export const getCases = async () => {
  const response = await axios.get('/api/v1/cases');
  return response.data;
};

export const createCase = async (caseData) => {
  const response = await axios.post('/api/v1/cases', caseData);
  return response.data;
};
```

**After (TypeScript):**
```typescript
// src/services/caseService.ts
import axios from 'axios';

export interface Case {
  case_id: string;
  name: string;
  description?: string;
  status: 'open' | 'in_progress' | 'closed';
  created_at: string;
  updated_at: string;
}

export interface CreateCaseDto {
  name: string;
  description?: string;
}

export const getCases = async (): Promise<Case[]> => {
  const response = await axios.get<Case[]>('/api/v1/cases');
  return response.data;
};

export const createCase = async (caseData: CreateCaseDto): Promise<Case> => {
  const response = await axios.post<Case>('/api/v1/cases', caseData);
  return response.data;
};
```

### Example 3: Custom Hook

**Before (JavaScript):**
```javascript
// src/hooks/useCases.js
import { useState, useEffect } from 'react';
import { getCases } from '@services/caseService';

export const useCases = () => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await getCases();
        setCases(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCases();
  }, []);

  return { cases, loading, error };
};
```

**After (TypeScript):**
```typescript
// src/hooks/useCases.ts
import { useState, useEffect } from 'react';
import { getCases, Case } from '@services/caseService';

interface UseCasesReturn {
  cases: Case[];
  loading: boolean;
  error: string | null;
}

export const useCases = (): UseCasesReturn => {
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const data = await getCases();
        setCases(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchCases();
  }, []);

  return { cases, loading, error };
};
```

### Example 4: Redux Slice

**Before (JavaScript):**
```javascript
// src/store/slices/caseSlice.js
import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  cases: [],
  selectedCase: null,
  loading: false,
  error: null,
};

const caseSlice = createSlice({
  name: 'cases',
  initialState,
  reducers: {
    setCases: (state, action) => {
      state.cases = action.payload;
    },
    selectCase: (state, action) => {
      state.selectedCase = action.payload;
    },
  },
});

export const { setCases, selectCase } = caseSlice.actions;
export default caseSlice.reducer;
```

**After (TypeScript):**
```typescript
// src/store/slices/caseSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Case } from '@services/caseService';

interface CaseState {
  cases: Case[];
  selectedCase: Case | null;
  loading: boolean;
  error: string | null;
}

const initialState: CaseState = {
  cases: [],
  selectedCase: null,
  loading: false,
  error: null,
};

const caseSlice = createSlice({
  name: 'cases',
  initialState,
  reducers: {
    setCases: (state, action: PayloadAction<Case[]>) => {
      state.cases = action.payload;
    },
    selectCase: (state, action: PayloadAction<Case>) => {
      state.selectedCase = action.payload;
    },
  },
});

export const { setCases, selectCase } = caseSlice.actions;
export default caseSlice.reducer;
```

---

## 🔄 Migration Workflow

### Step-by-Step Process

1. **Start with Types/Interfaces**
   - Create `src/types` directory
   - Define common types and interfaces
   - Export from central location

2. **Convert Utilities First**
   - Convert pure functions
   - Add proper type annotations
   - Test thoroughly

3. **Convert Services**
   - Define API response types
   - Add request/response interfaces
   - Update axios calls with generics

4. **Convert Hooks**
   - Add return type annotations
   - Define parameter types
   - Use proper React types

5. **Convert Components**
   - Start with leaf components
   - Define Props interfaces
   - Move up the component tree

6. **Convert Pages**
   - Last step after all components are converted
   - Add route typing if using TypeScript router

---

## 📚 Common Types

Create `src/types/index.ts` with common types:

```typescript
// Common API types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}

// Case types
export interface Case {
  case_id: string;
  name: string;
  description?: string;
  status: CaseStatus;
  priority: CasePriority;
  created_at: string;
  updated_at: string;
  created_by: string;
  assigned_to?: string;
}

export type CaseStatus = 'open' | 'in_progress' | 'closed' | 'archived';
export type CasePriority = 'low' | 'medium' | 'high' | 'critical';

// Investigation types
export interface Investigation {
  id: string;
  case_id: string;
  type: InvestigationType;
  status: InvestigationStatus;
  results?: any;
  started_at: string;
  completed_at?: string;
}

export type InvestigationType = 'm365' | 'endpoint' | 'credentials' | 'hunting';
export type InvestigationStatus = 'pending' | 'running' | 'completed' | 'failed';

// User types
export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  permissions: Permission[];
}

export type UserRole = 'admin' | 'analyst' | 'viewer';
export type Permission = 'read' | 'write' | 'delete' | 'execute';
```

---

## 🧪 Testing with TypeScript

Update test files to use TypeScript:

```typescript
// src/components/Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button Component', () => {
  it('renders correctly', () => {
    render(<Button onClick={() => {}}>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);
    
    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

---

## ⚠️ Common Pitfalls

### 1. Using `any` Type

❌ **Don't:**
```typescript
const processData = (data: any) => {
  return data.map((item: any) => item.name);
};
```

✅ **Do:**
```typescript
interface DataItem {
  name: string;
  value: number;
}

const processData = (data: DataItem[]) => {
  return data.map(item => item.name);
};
```

### 2. Not Typing Event Handlers

❌ **Don't:**
```typescript
const handleClick = (e) => {
  e.preventDefault();
};
```

✅ **Do:**
```typescript
import { MouseEvent } from 'react';

const handleClick = (e: MouseEvent<HTMLButtonElement>) => {
  e.preventDefault();
};
```

### 3. Ignoring Null/Undefined

❌ **Don't:**
```typescript
const getName = (user) => {
  return user.name;
};
```

✅ **Do:**
```typescript
const getName = (user: User | null) => {
  return user?.name ?? 'Unknown';
};
```

---

## 📊 Progress Tracking

Track migration progress:

```bash
# Count TypeScript files
find src -name "*.ts" -o -name "*.tsx" | wc -l

# Count JavaScript files remaining
find src -name "*.js" -o -name "*.jsx" | wc -l

# Calculate percentage
# (TS files / Total files) * 100
```

Current status:
- Total files: 91
- Converted: 0
- Remaining: 91
- Progress: 0%

---

## 🚀 Benefits After Migration

Expected improvements:

- **15-20% reduction** in runtime errors
- **30% faster** development with better IDE support
- **50% easier** refactoring with type safety
- **Better onboarding** for new developers
- **Self-documenting** codebase

---

## 📖 Resources

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
- [Migrating from JavaScript](https://www.typescriptlang.org/docs/handbook/migrating-from-javascript.html)

---

**Last Updated:** December 16, 2024  
**Version:** 1.0  
**Status:** Setup Complete, Migration In Progress

import { configureStore } from '@reduxjs/toolkit';
import caseReducer from './reducers/caseReducer';

export const store = configureStore({
  reducer: {
    cases: caseReducer
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['cases/fetchCases/pending', 'cases/fetchCases/fulfilled', 'cases/fetchCases/rejected']
      }
    }),
  devTools: import.meta.env.VITE_DEBUG === 'true'
});

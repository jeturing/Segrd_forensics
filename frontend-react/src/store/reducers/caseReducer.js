import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { caseService } from '../../services/cases';

export const fetchCases = createAsyncThunk(
  'cases/fetchCases',
  async ({ page = 1, limit = 10 }, { rejectWithValue }) => {
    try {
      const data = await caseService.getCases(page, limit);
      return data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Error fetching cases');
    }
  }
);

export const createCase = createAsyncThunk(
  'cases/createCase',
  async (caseData, { rejectWithValue }) => {
    try {
      const data = await caseService.createCase(caseData);
      return data;
    } catch (error) {
      return rejectWithValue(error.response?.data || 'Error creating case');
    }
  }
);

const initialState = {
  items: [],
  selectedCase: null,
  loading: false,
  error: null,
  pagination: {
    page: 1,
    limit: 10,
    total: 0
  }
};

const caseSlice = createSlice({
  name: 'cases',
  initialState,
  reducers: {
    selectCase: (state, action) => {
      state.selectedCase = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCases.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCases.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items || [];
        state.pagination = action.payload.pagination || state.pagination;
      })
      .addCase(fetchCases.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createCase.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createCase.fulfilled, (state, action) => {
        state.loading = false;
        state.items.unshift(action.payload);
      })
      .addCase(createCase.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  }
});

export const { selectCase, clearError } = caseSlice.actions;
export default caseSlice.reducer;

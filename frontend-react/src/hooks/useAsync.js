import { useState, useCallback } from 'react';

export default function useAsync(initialValue) {
  const [status, setStatus] = useState('idle');
  const [data, setData] = useState(initialValue);
  const [error, setError] = useState(null);

  const run = useCallback(async (promise) => {
    setStatus('pending');
    try {
      const result = await promise;
      setData(result);
      setStatus('success');
      return result;
    } catch (err) {
      setError(err);
      setStatus('error');
      throw err;
    }
  }, []);

  return { status, data, error, run };
}

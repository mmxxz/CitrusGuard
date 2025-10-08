import { useLayoutEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthWrapper = ({ children }: { children: React.ReactNode }) => {
  const navigate = useNavigate();
  const [isReady, setIsReady] = useState(false);

  useLayoutEffect(() => {
    const authToken = localStorage.getItem('authToken');
    if (!authToken) {
      navigate('/login', { replace: true });
    } else {
      setIsReady(true);
    }
  }, [navigate]);

  return isReady ? <>{children}</> : null;
};

export default AuthWrapper;
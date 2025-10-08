import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TreePine, Mail, Lock } from 'lucide-react';

import { login } from '../services/apiClient';
import { useAppStore } from '../lib/store';

const Login = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState(''); // In backend this is email
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const fetchInitialData = useAppStore((state) => state.fetchInitialData);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email); // FastAPI OAuth2 uses 'username'
      formData.append('password', password);

      const response = await login(formData);
      const { access_token } = response.data;
      localStorage.setItem('authToken', access_token);

      // Fetch user data and check if onboarding is needed
      await fetchInitialData();
      const hasCompletedOnboarding = localStorage.getItem('hasCompletedOnboarding');
      if (!hasCompletedOnboarding) {
        navigate('/orchard-setup', { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    } catch (err) {
      setError('Failed to login. Please check your credentials.');
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center shadow-sm mb-4">
            <TreePine className="w-10 h-10 text-green-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800">
            CitrusGuard AI
          </h1>
          <p className="text-gray-600 mt-2">智慧果园管理</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="text-sm font-medium text-gray-700">邮箱地址</label>
            <div className="relative mt-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl"
                placeholder="请输入您的邮箱地址"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">密码</label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl"
                placeholder="请输入您的密码"
                required
              />
            </div>
          </div>

          <div className="pt-4">
            <button
              type="submit"
              className="w-full bg-green-600 text-white rounded-2xl py-3 text-lg font-semibold shadow-lg active:scale-95 transition-transform"
            >
              登录
            </button>
          </div>
          
          <div className="flex justify-between text-sm text-gray-600">
            <a href="#" onClick={() => navigate('/register')} className="hover:underline">注册新账户</a>
            <a href="#" className="hover:underline">忘记密码?</a>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;
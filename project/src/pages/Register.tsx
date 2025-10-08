import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Mail } from 'lucide-react';

import { register, login } from '../services/apiClient';

const Register = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState(''); // This is email in the backend
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError("Passwords do not match!");
      return;
    }
    setError('');
    try {
      await register({ 
        email: email, 
        password: password, 
        full_name: "New User",
        is_active: true,
        is_superuser: false
      });
      
      // Automatically log in the user after registration
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      const response = await login(formData);
      localStorage.setItem('authToken', response.data.access_token);

      navigate('/orchard-setup', { replace: true });
    } catch (err: any) {
      console.error('Registration error:', err);
      console.error('Error response:', err.response?.data);
      if (err.response?.data?.detail) {
        setError(`Registration failed: ${err.response.data.detail}`);
      } else if (err.response?.status === 422) {
        setError(`Registration failed: Invalid data format. Details: ${JSON.stringify(err.response.data)}`);
      } else {
        setError('Registration failed. The email might already be in use.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 flex flex-col justify-center items-center">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">创建新账户</h1>
          <p className="text-gray-600 mt-2">欢迎加入 CitrusGuard AI</p>
        </div>

        <form onSubmit={handleRegister} className="space-y-6">
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
            <label className="text-sm font-medium text-gray-700">设置密码</label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl"
                placeholder="请输入密码"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">确认密码</label>
            <div className="relative mt-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl"
                placeholder="请再次输入密码"
                required
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div className="pt-4">
            <button
              type="submit"
              className="w-full bg-green-600 text-white rounded-2xl py-3 text-lg font-semibold shadow-lg active:scale-95 transition-transform"
            >
              注册并创建果园
            </button>
          </div>
          
          <div className="text-center text-sm text-gray-600">
            <a href="#" onClick={() => navigate('/login')} className="hover:underline">已有账户？直接登录</a>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Register;

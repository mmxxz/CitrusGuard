import { useNavigate } from 'react-router-dom';

interface SmartOrchardProps {
  healthScore: number;
  riskAlerts: { id: string; level: 'high' | 'medium' | 'low' }[];
  weatherCondition: 'sunny' | 'cloudy' | 'rainy';
}

const SmartOrchard = ({ healthScore, riskAlerts, weatherCondition }: SmartOrchardProps) => {
  const navigate = useNavigate();
  const treeHealth = healthScore / 100;
  const leafColor = treeHealth > 0.8 ? 'text-green-500' : treeHealth > 0.6 ? 'text-yellow-500' : 'text-red-500';

  return (
    <div className="relative flex justify-center items-end h-40 my-8">
      <div className="w-4 h-20 bg-gradient-to-t from-amber-800 to-amber-600 rounded-t"></div>
      <div className={`absolute bottom-16 w-24 h-24 ${leafColor} opacity-90`}>
        <svg viewBox="0 0 100 100" fill="currentColor">
          <circle cx="50" cy="50" r="40" />
          <circle cx="30" cy="40" r="25" />
          <circle cx="70" cy="40" r="25" />
          <circle cx="35" cy="65" r="20" />
          <circle cx="65" cy="65" r="20" />
        </svg>
      </div>
      {Array.isArray(riskAlerts) && riskAlerts.filter(alert => alert.level === 'high').map((alert, index) => (
        <div
          key={alert.id}
          className="absolute bottom-20 left-1/2 w-3 h-3 bg-red-500 rounded-full animate-pulse cursor-pointer"
          style={{ transform: `translateX(${index * 20 - 50}%)` }}
          onClick={() => navigate('/alerts')}
        />
      ))}
      {weatherCondition === 'rainy' && (
        <div className="absolute inset-0 pointer-events-none">
          {[...Array(10)].map((_, i) => (
            <div
              key={i}
              className="absolute w-px h-4 bg-blue-400 opacity-60 animate-bounce"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 50}%`,
                animationDelay: `${Math.random() * 2}s`
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default SmartOrchard;

import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, MapPin, Sprout, Calendar, ChevronsUpDown } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { createOrchard, updateOrchard } from '../services/apiClient';

const OrchardSetup = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { orchard: existingOrchard, fetchInitialData } = useAppStore();
  
  const isEditMode = location.pathname.includes('edit');
  const orchardToEdit = isEditMode ? existingOrchard : null;

  const [orchardName, setOrchardName] = useState(orchardToEdit?.name || '');
  const [locationName, setLocationName] = useState('中国，四川省成都市');
  const [variety, setVariety] = useState('不知火柑');
  const [avgAge, setAvgAge] = useState(5);
  const [lastHarvest, setLastHarvest] = useState('2023-11-15');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const orchardData = {
      name: orchardName,
      address_detail: locationName,
      main_variety: variety,
      avg_tree_age: avgAge,
      last_harvest_date: lastHarvest,
    };
    
    try {
      if (isEditMode && orchardToEdit) {
        await updateOrchard(orchardToEdit.id, orchardData);
      } else {
        await createOrchard(orchardData);
      }
      
      localStorage.setItem('hasCompletedOnboarding', 'true');
      await fetchInitialData();
      
      navigate('/');
    } catch (error) {
      console.error("Failed to save orchard", error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 flex justify-center items-center">
      <div className="w-full max-w-sm">
        <div className="flex items-center mb-8">
          {isEditMode && (
            <button onClick={() => navigate('/')} className="mr-4">
              <ArrowLeft className="w-6 h-6" />
            </button>
          )}
          <h1 className="text-2xl font-bold text-gray-800">
            {isEditMode ? '编辑果园档案' : '创建您的果园档案'}
          </h1>
        </div>
        <p className="text-gray-600 mb-8">
          {isEditMode ? '更新您的果园信息。' : '输入基本信息，让AI更懂您的果园。'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="text-sm font-medium text-gray-700">果园名称</label>
            <input
              type="text"
              value={orchardName}
              onChange={(e) => setOrchardName(e.target.value)}
              className="w-full mt-1 p-3 border border-gray-300 rounded-xl"
              placeholder="例如：王先生的阳光果园"
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">果园位置</label>
            <div className="relative mt-1">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={locationName}
                onChange={(e) => setLocationName(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">主要柑橘品种</label>
            <div className="relative mt-1">
              <Sprout className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <select
                value={variety}
                onChange={(e) => setVariety(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl appearance-none"
              >
                <option>不知火柑</option>
                <option>春见</option>
                <option>爱媛</option>
              </select>
              <ChevronsUpDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">果树平均树龄 (年)</label>
            <input
              type="number"
              value={avgAge}
              onChange={(e) => setAvgAge(parseInt(e.target.value, 10))}
              className="w-full mt-1 p-3 border border-gray-300 rounded-xl"
              required
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">最近一次采摘时间</label>
            <div className="relative mt-1">
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="date"
                value={lastHarvest}
                onChange={(e) => setLastHarvest(e.target.value)}
                className="w-full p-3 pl-10 border border-gray-300 rounded-xl"
                required
              />
            </div>
          </div>

          <div className="pt-4">
            <button
              type="submit"
              className="w-full bg-green-600 text-white rounded-2xl py-4 text-lg font-semibold shadow-lg active:scale-95 transition-transform"
            >
              {isEditMode ? '更新信息' : '保存并进入果园'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default OrchardSetup;

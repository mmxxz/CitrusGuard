import { FC, useState } from 'react';
import { FarmOperationCreate } from '../types';

interface FarmOperationFormProps {
  onSubmit: (data: FarmOperationCreate) => void;
  onCancel: () => void;
}

const FarmOperationForm: FC<FarmOperationFormProps> = ({ onSubmit, onCancel }) => {
  const [type, setType] = useState('spraying');
  const [description, setDescription] = useState('');
  const [materials, setMaterials] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      type,
      description,
      materials_used: materials.split(',').map(m => m.trim()),
      operation_date: date,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4 bg-white rounded-lg">
      <h3 className="text-lg font-semibold text-gray-800">记录农事操作</h3>
      <div>
        <label className="text-sm font-medium text-gray-700">操作类型</label>
        <select value={type} onChange={(e) => setType(e.target.value)} className="w-full mt-1 p-2 border rounded">
          <option value="spraying">喷洒</option>
          <option value="fertilizing">施肥</option>
          <option value="irrigation">灌溉</option>
          <option value="pruning">修剪</option>
          <option value="other">其他</option>
        </select>
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700">使用材料 (用逗号分隔)</label>
        <input type="text" value={materials} onChange={(e) => setMaterials(e.target.value)} className="w-full mt-1 p-2 border rounded" placeholder="例如: 波尔多液, 阿维菌素" />
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700">详细描述</label>
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full mt-1 p-2 border rounded" rows={3}></textarea>
      </div>
      <div>
        <label className="text-sm font-medium text-gray-700">操作日期</label>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full mt-1 p-2 border rounded" />
      </div>
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-200 rounded">取消</button>
        <button type="submit" className="px-4 py-2 bg-green-600 text-white rounded">保存</button>
      </div>
    </form>
  );
};

export default FarmOperationForm;

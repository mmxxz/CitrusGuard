import { FC } from 'react';
import { CheckCircle2 } from 'lucide-react';
import { DiagnosisResult } from '../types';

interface ResultCardProps {
  result: DiagnosisResult;
  onRecord: () => void;
}

const ResultCard: FC<ResultCardProps> = ({ result, onRecord }) => {
  return (
    <div className="bg-white border border-green-200 rounded-xl p-4 max-w-xs shadow-md">
      <div className="flex items-center gap-3 mb-4">
        <CheckCircle2 className="w-8 h-8 text-green-600" />
        <div>
          <h3 className="font-bold text-lg text-gray-800">诊断报告</h3>
          <p className="text-xs text-gray-500">{new Date(result.generated_at).toLocaleString()}</p>
        </div>
      </div>

      <div className="space-y-3 text-sm">
        <div>
          <p className="font-semibold text-gray-600">主要诊断</p>
          <p className="text-gray-800">{result.primary_diagnosis} (置信度: {(result.confidence * 100).toFixed(0)}%)</p>
        </div>
        {result.secondary_diagnoses?.length > 0 && (
          <div>
            <p className="font-semibold text-gray-600">次要可能性</p>
            <ul className="list-disc list-inside text-gray-700">
              {result.secondary_diagnoses.map(diag => (
                <li key={diag.name}>{diag.name} (置信度: {(diag.confidence * 100).toFixed(0)}%)</li>
              ))}
            </ul>
          </div>
        )}
        <div>
          <p className="font-semibold text-gray-600">防治建议</p>
          <p className="text-gray-700 whitespace-pre-wrap">{result.treatment_advice}</p>
        </div>
        <div>
          <p className="font-semibold text-gray-600">后续观察计划</p>
          <p className="text-gray-700 whitespace-pre-wrap">{result.follow_up_plan}</p>
        </div>
      </div>
      <button onClick={onRecord} className="w-full mt-4 bg-green-600 text-white rounded-lg py-2 text-sm font-medium">
        记录至病例档案
      </button>
    </div>
  );
};

export default ResultCard;
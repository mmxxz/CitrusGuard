import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, MessageCircle } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { getCases, getCaseDetail, recordFarmOperation } from '../services/apiClient';
import { CaseFile, DiagnosisResult, FarmOperationCreate } from '../types';
import Spinner from '../components/Spinner';
import FarmOperationForm from '../components/FarmOperationForm';
import CaseChatModal from '../components/CaseChatModal'; // Import the new component

const Cases = () => {
  const navigate = useNavigate();
  const { orchard } = useAppStore();
  const [cases, setCases] = useState<CaseFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<DiagnosisResult | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [showRecordModal, setShowRecordModal] = useState(false);
  const [showChatModal, setShowChatModal] = useState(false); // State for chat modal
  const [currentCaseId, setCurrentCaseId] = useState<string | null>(null);

  useEffect(() => {
    if (orchard) {
      fetchCases();
    }
  }, [orchard]);

  const fetchCases = async () => {
    if (!orchard) return;
    try {
      setIsLoading(true);
      const response = await getCases(orchard.id);
      setCases(response.data);
    } catch (error) {
      console.error("Failed to fetch cases", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewDetail = async (caseId: string) => {
    if (!orchard) return;
    try {
      const response = await getCaseDetail(orchard.id, caseId);
      setSelectedCase(response.data);
      setCurrentCaseId(caseId); // Set current case ID for chat
      setShowDetailModal(true);
    } catch (error) {
      console.error("Failed to fetch case detail", error);
      alert("获取病例详情失败，请重试");
    }
  };

  const handleRecordOperation = (caseId: string) => {
    setCurrentCaseId(caseId);
    setShowRecordModal(true);
  };

  const handleOpenChat = () => {
    if (!currentCaseId) return;
    setShowDetailModal(false); // Close detail modal
    setShowChatModal(true);   // Open chat modal
  };

  const handleSubmitOperation = async (operationData: FarmOperationCreate) => {
    if (!orchard || !currentCaseId) return;
    try {
      await recordFarmOperation(orchard.id, currentCaseId, operationData);
      alert("防治记录已保存");
      setShowRecordModal(false);
      setCurrentCaseId(null);
      fetchCases(); // Refresh case list
    } catch (error) {
      console.error("Failed to record operation", error);
      alert("保存防治记录失败，请重试");
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen"><Spinner /></div>;
  }

  return (
    <div className="min-h-full bg-gray-50">
      <header className="bg-white px-4 py-3 flex items-center shadow-sm sticky top-0 z-10">
        <button onClick={() => navigate('/')}><ArrowLeft className="w-6 h-6" /></button>
        <h1 className="flex-1 text-center text-lg font-semibold">病例档案库</h1>
        <button><Search className="w-6 h-6 text-gray-600" /></button>
      </header>

      <main className="p-4 space-y-3">
        {cases.length === 0 && (
          <div className="text-center py-12 text-gray-500"><p>暂无病例档案</p></div>
        )}
        {cases.map(caseFile => (
          <div key={caseFile.id} className="bg-white rounded-2xl p-4 shadow-sm">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-800">{caseFile.diagnosis}</h3>
                <p className="text-sm text-gray-500">{new Date(caseFile.date).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${caseFile.status === 'resolved' ? 'bg-green-500' : 'bg-orange-500'}`}></span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  caseFile.severity === 'high' ? 'bg-red-100 text-red-700' :
                  caseFile.severity === 'medium' ? 'bg-orange-100 text-orange-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}>
                  {caseFile.severity === 'high' ? '严重' : caseFile.severity === 'medium' ? '中等' : '轻微'}
                </span>
              </div>
            </div>
            
            <div className="flex gap-2">
              <button onClick={() => handleViewDetail(caseFile.id)} className="flex-1 bg-gray-100 text-gray-600 rounded-xl py-2 text-sm font-medium">
                查看详情
              </button>
              {caseFile.status === 'active' && (
                <button onClick={() => handleRecordOperation(caseFile.id)} className="flex-1 bg-blue-600 text-white rounded-xl py-2 text-sm font-medium">
                  记录防治
                </button>
              )}
            </div>
          </div>
        ))}
      </main>

      {/* 详情模态框 */}
      {showDetailModal && selectedCase && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-800">病例详情</h2>
              <button onClick={() => setShowDetailModal(false)} className="text-gray-500">✕</button>
            </div>
            <div className="space-y-4">
              {/* Details content */}
              <div><h3 className="font-semibold">主要诊断</h3><p>{selectedCase.primary_diagnosis}</p></div>
              <div><h3 className="font-semibold">防治建议</h3><p className="whitespace-pre-wrap">{selectedCase.treatment_advice}</p></div>
              <div><h3 className="font-semibold">预防建议</h3><p className="whitespace-pre-wrap">{selectedCase.prevention_advice}</p></div>
            </div>
            <div className="mt-6 flex gap-2">
              <button onClick={() => setShowDetailModal(false)} className="flex-1 bg-gray-100 rounded-xl py-2.5">关闭</button>
              <button onClick={handleOpenChat} className="flex-1 bg-green-600 text-white rounded-xl py-2.5 flex items-center justify-center gap-2">
                <MessageCircle size={18} />
                询问AI
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 记录防治模态框 */}
      {showRecordModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">记录防治操作</h2>
              <button onClick={() => setShowRecordModal(false)} className="text-gray-500">✕</button>
            </div>
            <FarmOperationForm onSubmit={handleSubmitOperation} />
          </div>
        </div>
      )}

      {/* AI 聊天模态框 */}
      {showChatModal && currentCaseId && (
        <CaseChatModal 
          caseId={currentCaseId}
          caseTitle={selectedCase?.primary_diagnosis || '病例'}
          onClose={() => setShowChatModal(false)}
        />
      )}
    </div>
  );
};

export default Cases;
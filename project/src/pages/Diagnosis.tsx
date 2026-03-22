import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Send, Camera, Image as ImageIcon, MessageCircle } from 'lucide-react';
import Modal from 'react-modal';
import { useAppStore } from '../lib/store';
import { startDiagnosis, continueDiagnosis, uploadImage, getDiagnosisResult, recordFarmOperation } from '../services/apiClient';
import { ChatMessage as ChatMessageType, DiagnosisResult, FarmOperationCreate } from '../types';
import Spinner from '../components/Spinner';
import Markdown from '../components/Markdown';
import ClarificationCard from '../components/ClarificationCard';
import ResultCard from '../components/ResultCard';
import FarmOperationForm from '../components/FarmOperationForm';
import { wsClient } from '../services/ws';
import { riskAlertDisplayName } from '../lib/riskAlert';

Modal.setAppElement('#root');

const Diagnosis = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { orchard } = useAppStore();
  const alertToConfirm = location.state?.alertToConfirm;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessageType[]>([]);
  const [inputText, setInputText] = useState('');
  const [pendingImages, setPendingImages] = useState<string[]>([]);
  const [isAIThinking, setIsAIThinking] = useState(false);
  const [showAttachmentMenu, setShowAttachmentMenu] = useState(false);
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnosisResult | null>(null);
  const [progress, setProgress] = useState({ percent: 0, step: '' });
  const [thinkingText, setThinkingText] = useState('');
  const [currentTurnId, setCurrentTurnId] = useState<number | null>(null);
  const currentTurnIdRef = useRef<number | null>(null);
  const getThinkingPreview = (text: string, maxLines: number = 5, fallbackChars: number = 400) => {
    if (!text) return '';
    const lines = text.split(/\r?\n/);
    if (lines.length > 1) return lines.slice(-maxLines).join('\n');
    return text.slice(-fallbackChars);
  };
  const stageMap: Record<string, string> = {
    'llm': '模型思考中…',
    'llm_done': '思考完成',
    'compose': '正在组织答案…',
    'chain': '执行链…',
  };
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const msgSeqRef = useRef(0);
  const genId = (prefix: string) => `${prefix}-${Date.now()}-${msgSeqRef.current++}`;
  const removePending = (idx: number) => setPendingImages(prev => prev.filter((_, i) => i !== idx));

  useEffect(() => {
    // 页面首次进入时重置所有会话相关状态，避免显示上次残留
    setSessionId(null);
    setChatMessages([]);
    setDiagnosisResult(null);
    setProgress({ percent: 0, step: '' });
    setThinkingText('');
  }, []);

  useEffect(() => {
    if (orchard && sessionId) {
      // 新会话/重连时，先清空思考累计，避免上一会话残留
      setThinkingText('');
      setCurrentTurnId(null);
      currentTurnIdRef.current = null;
      wsClient.connect(orchard.id, sessionId || '');
      wsClient.setOnMessageHandler((data: string) => {
        // 解析 TURN:<id>| 前缀，确保只渲染当前轮消息
        let payload = data;
        let turnId: number | null = null;
        if (data.startsWith('TURN:')) {
          const sep = data.indexOf('|');
          if (sep > 5) {
            turnId = Number(data.substring(5, sep));
            payload = data.substring(sep + 1);
          }
        }

        if (payload.startsWith("PROGRESS:")) {
          const [_, , raw] = payload.split(':');
          const friendly = stageMap[raw] || (raw?.startsWith('tool:') ? `调用工具：${raw.substring(5)}` : `执行：${raw}`);
          if (raw === 'agent_v2' || raw === 'agent_v2_reply' || raw === 'llm' || raw === 'compose') {
            setThinkingText('');
            if (turnId !== null) {
              setCurrentTurnId(turnId);
              currentTurnIdRef.current = turnId;
            }
          }
          setProgress({ percent: 1, step: friendly });
        } else if (payload.startsWith("THOUGHT:")) {
          const thought = payload.substring(8);
          // 仅处理当前回合的思考内容
          if (turnId !== null && currentTurnIdRef.current !== null && turnId !== currentTurnIdRef.current) {
            return;
          }
          setThinkingText(prev => {
            const next = (prev + thought).replace(/\r/g, '');
            const lines = next.split('\n');
            if (lines.length > 5) return lines.slice(-5).join('\n');
            const MAX_CHARS = 400;
            return next.length > MAX_CHARS ? next.slice(-MAX_CHARS) : next;
          });
        } else if (payload.startsWith("MESSAGE:")) {
          const messageJson = payload.substring(8);
          const aiMessage = JSON.parse(messageJson);
          handleNewAIMessage(aiMessage);
        } else if (payload.startsWith("RESULT_READY:")) {
          setThinkingText('');
          setCurrentTurnId(null);
          currentTurnIdRef.current = null;
          fetchResult();
        }
      });
    }
    return () => wsClient.disconnect();
  }, [orchard, sessionId]);

  useEffect(() => {
    if (!alertToConfirm) return;
    const label = riskAlertDisplayName(alertToConfirm);
    void handleSendMessage(
      `我在风险预警里看到「${label}」的中/高风险提示，想结合果园实际情况再确认一下风险，并看是否需要拍照诊断。`
    );
    // 清空路由状态，避免返回本页时再次自动触发
    navigate(location.pathname, { replace: true, state: {} });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 仅在进入页时根据路由 state 触发一次
  }, [alertToConfirm]);

  const fetchResult = async () => {
    if (orchard && sessionId) {
      const resultResponse = await getDiagnosisResult(orchard.id, sessionId);
      setDiagnosisResult(resultResponse.data);
      setIsAIThinking(false);
      setThinkingText('');
    }
  };

  const handleNewAIMessage = (aiResponse: any) => {
    // 处理智能体的JSON格式输出
    let messageType: 'text' | 'progress' | 'card' | 'clarification' | 'diagnosis_result' | 'diagnosis_report' = 'text';
    let content = '';
    let options = [];
    let primary_diagnosis = '';
    let confidence = 0;
    let secondary_diagnoses = [];
    let prevention_advice = '';
    let treatment_advice = '';
    
    if (typeof aiResponse === 'string') {
      try {
        // 尝试解析JSON字符串
        const parsed = JSON.parse(aiResponse);
        messageType = parsed.type || 'text';
        content = parsed.content || '';
        options = parsed.options || [];
        primary_diagnosis = parsed.primary_diagnosis || '';
        confidence = parsed.confidence || 0;
        secondary_diagnoses = parsed.secondary_diagnoses || [];
        prevention_advice = parsed.prevention_advice || '';
        treatment_advice = parsed.treatment_advice || '';
      } catch {
        // 如果不是JSON，作为普通文本处理
        content = aiResponse;
      }
    } else {
      // 直接是对象
      messageType = aiResponse.type || 'text';
      content = aiResponse.content || '';
      options = aiResponse.options || [];
      primary_diagnosis = aiResponse.primary_diagnosis || '';
      confidence = aiResponse.confidence || 0;
      secondary_diagnoses = aiResponse.secondary_diagnoses || [];
      prevention_advice = aiResponse.prevention_advice || '';
      treatment_advice = aiResponse.treatment_advice || '';
    }
    
    const aiMessage: ChatMessageType = {
      id: genId('ai'), 
      sender: 'ai', 
      type: messageType,
      content: content, 
      options: options,
      primary_diagnosis: primary_diagnosis,
      confidence: confidence,
      secondary_diagnoses: secondary_diagnoses,
      prevention_advice: prevention_advice,
      treatment_advice: treatment_advice,
      timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, aiMessage]);
    setProgress({ percent: 0, step: '' });
    setIsAIThinking(false);
    setThinkingText('');
  };

  const handleSendMessage = async (content: string, imageUrl: string | null = null) => {
    if (!content.trim() && !imageUrl && pendingImages.length === 0) return;
    if (!orchard) return;

    // 关键字触发表单：最小实现，使用 prompt 收集关键信息
    const textLower = content.trim().toLowerCase();
    if (textLower === '诊断' || textLower === 'diagnose') {
      setIsAIThinking(true);
      // 简易表单字段（可后续替换为自定义 Modal 表单）
      const variety = window.prompt('品种（可留空）', '') || '未知';
      const stage = window.prompt('当前生育期（春梢/夏梢/秋梢/开花/幼果/膨大/转色/采后）', '') || '未知';
      const part = window.prompt('主要问题部位（如：叶片/果实/枝干/根部/整株）', '') || '未知';
      const symptom = window.prompt('症状要点（如：黄化/斑点/卷叶/油渍状/霉层）', '') || '未知';
      const env = window.prompt('近期天气/管理（如：连续阴雨/有施肥/有用药/渍涝/干旱）', '') || '未知';

      const synthesized = [
        '以下是收集到的柑橘病症信息：',
        `- 基本信息: 品种:${variety}, 生育期:${stage}。`,
        `- 主要问题部位: ${part}。`,
        `- 具体症状: 在${part}观察到${symptom}。`,
        `- 环境与管理: ${env}。`,
        '\n请根据以上信息进行诊断。'
      ].join('\n');

      // 将合成描述发送
      await handleSendMessage(synthesized, imageUrl);
      setIsAIThinking(false);
      return;
    }

    setIsAIThinking(true);
    setThinkingText('');
    setInputText('');
    
    const userMessage: ChatMessageType = {
      id: genId('msg'), sender: 'user', type: 'text',
      content: content || (pendingImages.length ? '[发送了图片]' : ''),
      image: imageUrl || undefined, timestamp: new Date().toISOString(),
    };
    setChatMessages(prev => [...prev, userMessage]);

    try {
      let currentSessionId = sessionId;
      if (!currentSessionId) {
        const imgs = [ ...(imageUrl ? [imageUrl] : []), ...pendingImages ];
        const response = await startDiagnosis(orchard.id, { initial_description: content, image_urls: imgs.length ? imgs : undefined });
        currentSessionId = response.data.session_id;
        // 拿到新会话ID后再次清空，避免与首次推送并发造成残留
        setThinkingText('');
        setSessionId(currentSessionId);
      } else {
        const imgs = [ ...(imageUrl ? [imageUrl] : []), ...pendingImages ];
        await continueDiagnosis(orchard.id, currentSessionId || '', { user_input: content || (imgs.length ? '[图片说明]' : ''), image_urls: imgs.length ? imgs : undefined });
      }
      setPendingImages([]);
    } catch (error) {
      console.error("Failed to send message", error);
      setIsAIThinking(false);
    }
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !orchard) return;

    setShowAttachmentMenu(false);

    try {
      const uploadResponse = await uploadImage(file);
      const imageUrl = uploadResponse.data.image_url;
      setPendingImages(prev => [...prev, imageUrl]);
    } catch (error) {
      console.error("Failed to upload image", error);
    }
  };

  const handleRecordOperation = async (data: FarmOperationCreate) => {
    if (!orchard || !diagnosisResult) return;
    try {
      await recordFarmOperation(orchard.id, diagnosisResult.id, data);
      setIsModalOpen(false);
      alert("农事记录已成功保存！");
      navigate('/cases');
    } catch (error) {
      console.error("Failed to record farm operation", error);
      alert("保存失败，请重试。");
    }
  };

  return (
    <div className="max-w-md mx-auto">
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <div className="bg-white px-4 py-3 flex items-center shadow-sm sticky top-0 z-10">
          <button onClick={() => navigate(-1)}><ArrowLeft className="w-6 h-6" /></button>
          <h1 className="flex-1 text-center text-lg font-semibold">诊断实验室</h1>
          <div className="w-6"></div>
        </div>

        <div className="flex-1 p-4 space-y-4 overflow-y-auto">
          {chatMessages.length === 0 && !isAIThinking && (
            <div className="text-center py-12 text-gray-500">
              <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p>请描述症状或上传图片开始诊断</p>
            </div>
          )}
          {chatMessages.map(message => (
            <div key={message.id} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              {message.type === 'clarification' ? (
                <ClarificationCard question={message.content} options={message.options || []} onOptionSelect={(option) => handleSendMessage(option)} />
              ) : message.type === 'diagnosis_report' ? (
                <div className="max-w-2xl rounded-2xl p-4 bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 shadow-sm">
                  <div className="flex items-center gap-2 text-green-700 font-semibold mb-3">
                    <span>📋</span>
                    <span>诊断报告</span>
                  </div>
                  
                  {message.primary_diagnosis && (
                    <div className="mb-3">
                      <div className="font-medium text-gray-700 mb-1">主要诊断</div>
                      <div className="text-sm text-gray-800">
                        {message.primary_diagnosis} 
                        {message.confidence && ` (置信度: ${(message.confidence * 100).toFixed(0)}%)`}
                      </div>
                    </div>
                  )}
                  
                  {message.secondary_diagnoses && message.secondary_diagnoses.length > 0 && (
                    <div className="mb-3">
                      <div className="font-medium text-gray-700 mb-1">次要可能性</div>
                      <ul className="text-sm text-gray-800 list-disc list-inside">
                        {message.secondary_diagnoses.map((diag: any, index: number) => (
                          <li key={index}>
                            {diag.name} (置信度: {(diag.confidence * 100).toFixed(0)}%)
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {message.content && (
                    <div className="mb-3">
                      <div className="font-medium text-gray-700 mb-1">详细分析</div>
                      <Markdown className="text-[14px] leading-7" content={message.content.replace(/\\n/g, '\n')} />
                    </div>
                  )}
                  
                  {message.prevention_advice && (
                    <div className="mb-3">
                      <div className="font-medium text-gray-700 mb-1">预防建议</div>
                      <div className="text-sm whitespace-pre-wrap text-gray-800">
                        {message.prevention_advice.replace(/\\n/g, '\n')}
                      </div>
                    </div>
                  )}
                  
                  {message.treatment_advice && (
                    <div className="mb-3">
                      <div className="font-medium text-gray-700 mb-1">治疗建议</div>
                      <div className="text-sm whitespace-pre-wrap text-gray-800">
                        {message.treatment_advice.replace(/\\n/g, '\n')}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className={`max-w-2xl rounded-xl p-3 ${message.sender === 'user' ? 'bg-green-600 text-white' : 'bg-white border'}`}>
                  {message.content && (
                    message.sender === 'user' ? (
                      <p className="text-sm whitespace-pre-wrap">{message.content.replace(/\\n/g, '\n')}</p>
                    ) : (
                      <Markdown className="text-[14px] leading-7" content={message.content.replace(/\\n/g, '\n')} />
                    )
                  )}
                  {message.image && <img src={message.image} alt="诊断图片" className="mt-2 rounded-lg w-full max-w-xs" />}
                </div>
              )}
            </div>
          ))}
          {diagnosisResult && <ResultCard result={diagnosisResult} onRecord={() => setIsModalOpen(true)} />}
          {isAIThinking && (
            <div className="space-y-2 p-2">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <Spinner size={16} />
                <span>{progress.step || 'AI 正在分析...'}</span>
              </div>
              {thinkingText && (
                <div className="text-xs text-gray-500 whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded-md p-2 max-w-xs">
                  {getThinkingPreview(thinkingText, 5)}
                </div>
              )}
            </div>
          )}
          {pendingImages.length > 0 && (
            <div className="p-2 bg-amber-50 border border-amber-200 rounded-md">
              <div className="text-xs text-amber-700 mb-2">已添加 {pendingImages.length} 张图片，点击“发送”一并提交。</div>
              <div className="flex gap-2 overflow-x-auto">
                {pendingImages.map((url, idx) => (
                  <div key={idx} className="relative w-16 h-16 rounded overflow-hidden border">
                    <img src={url} className="object-cover w-full h-full" />
                    <button onClick={() => removePending(idx)} className="absolute -top-1 -right-1 w-5 h-5 bg-white/90 text-gray-700 rounded-full border leading-none">×</button>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="bg-white p-4 border-t border-gray-200 relative">
          {showAttachmentMenu && (
            <div className="absolute bottom-20 left-4 w-48 bg-white rounded-xl shadow-lg border p-2">
              <button onClick={() => { cameraInputRef.current?.click(); setShowAttachmentMenu(false); }} className="w-full flex items-center gap-3 p-2 hover:bg-gray-100 rounded-lg">
                <Camera className="w-5 h-5" /><span>拍照</span>
              </button>
              <button onClick={() => { fileInputRef.current?.click(); setShowAttachmentMenu(false); }} className="w-full flex items-center gap-3 p-2 hover:bg-gray-100 rounded-lg">
                <ImageIcon className="w-5 h-5" /><span>从相册选择</span>
              </button>
            </div>
          )}
          <div className="flex items-end gap-2">
            <button onClick={() => setShowAttachmentMenu(prev => !prev)} className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
              <Plus className="w-5 h-5 text-gray-600" />
            </button>
            <div className="flex-1 bg-gray-100 rounded-full px-4 py-2">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage(inputText)}
                placeholder="描述症状..."
                className="w-full bg-transparent outline-none text-sm"
              />
            </div>
            <button onClick={() => handleSendMessage(inputText)} disabled={(inputText.trim() === '' && pendingImages.length === 0) || isAIThinking} className="relative w-10 h-10 bg-green-600 rounded-full flex items-center justify-center disabled:opacity-50">
              <Send className="w-5 h-5 text-white" />
              {pendingImages.length > 0 && (
                <span className="absolute -top-1 -right-1 text-[10px] bg-white text-green-700 border rounded-full w-4 h-4 flex items-center justify-center">
                  {pendingImages.length}
                </span>
              )}
            </button>
          </div>
        </div>
        
        <input type="file" accept="image/*" ref={fileInputRef} onChange={handleFileSelect} className="hidden" />
        <input type="file" accept="image/*" capture="environment" ref={cameraInputRef} onChange={handleFileSelect} className="hidden" />
      </div>
      <Modal
        isOpen={isModalOpen}
        onRequestClose={() => setIsModalOpen(false)}
        contentLabel="Record Farm Operation"
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-transparent w-full max-w-md p-4"
        overlayClassName="fixed inset-0 bg-black bg-opacity-50 z-20"
      >
        <FarmOperationForm
          onSubmit={handleRecordOperation}
          onCancel={() => setIsModalOpen(false)}
        />
      </Modal>
    </div>
  );
};

export default Diagnosis;

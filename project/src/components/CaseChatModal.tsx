import { useState, useEffect, useRef } from 'react';
import { Send, X, Bot, User } from 'lucide-react';
import { askCaseQuestion } from '../services/apiClient';
import Spinner from './Spinner';

interface Message {
  sender: 'user' | 'ai';
  text: string;
}

interface CaseChatModalProps {
  caseId: string;
  caseTitle: string;
  onClose: () => void;
}

const CaseChatModal = ({ caseId, caseTitle, onClose }: CaseChatModalProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    // Initial greeting from AI
    setMessages([{
      sender: 'ai',
      text: `你好！我是您的AI农艺师。您可以问我关于病例 "${caseTitle}" 的任何问题。`
    }]);
  }, [caseTitle]);

  const handleSend = async () => {
    if (input.trim() === '' || isLoading) return;

    const userMessage: Message = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await askCaseQuestion(caseId, input);
      const aiMessage: Message = { sender: 'ai', text: response.data.answer };
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Failed to get AI answer", error);
      const errorMessage: Message = { 
        sender: 'ai', 
        text: '抱歉，AI服务暂时无法连接，请稍后再试。' 
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-60">
      <div className="bg-white rounded-2xl flex flex-col max-w-md w-full h-[85vh] max-h-[700px]">
        <header className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-800 truncate pr-4">询问AI: {caseTitle}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700 p-1">
            <X size={24} />
          </button>
        </header>

        <main className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.map((msg, index) => (
            <div key={index} className={`flex items-start gap-3 ${msg.sender === 'user' ? 'justify-end' : ''}`}>
              {msg.sender === 'ai' && (
                <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot size={20} />
                </div>
              )}
              <div className={`px-4 py-2 rounded-2xl max-w-xs md:max-w-sm ${
                msg.sender === 'user' 
                  ? 'bg-blue-500 text-white rounded-br-lg' 
                  : 'bg-gray-100 text-gray-800 rounded-bl-lg'
              }`}>
                <p className="text-sm whitespace-pre-wrap">{msg.text}</p>
              </div>
              {msg.sender === 'user' && (
                 <div className="w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center flex-shrink-0">
                  <User size={20} />
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-green-600 text-white rounded-full flex items-center justify-center flex-shrink-0">
                <Bot size={20} />
              </div>
              <div className="px-4 py-2 rounded-2xl bg-gray-100 text-gray-800 rounded-bl-lg">
                <Spinner size={20} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        <footer className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="输入您的问题..."
              className="flex-1 w-full bg-gray-100 border-transparent rounded-xl py-2 px-4 focus:outline-none focus:ring-2 focus:ring-green-500"
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || input.trim() === ''}
              className="bg-green-600 text-white rounded-full p-3 disabled:bg-gray-400 disabled:cursor-not-allowed hover:bg-green-700 transition-colors"
            >
              <Send size={20} />
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default CaseChatModal;

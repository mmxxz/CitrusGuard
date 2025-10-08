import { FC } from 'react';

interface ClarificationCardProps {
  question: string;
  options: string[];
  onOptionSelect: (option: string) => void;
}

const ClarificationCard: FC<ClarificationCardProps> = ({ question, options, onOptionSelect }) => {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 max-w-xs">
      <p className="text-sm font-semibold text-blue-800 mb-3">{question}</p>
      <div className="flex flex-col gap-2">
        {options.map((option) => (
          <button
            key={option}
            onClick={() => onOptionSelect(option)}
            className="w-full text-left bg-white border border-blue-300 text-blue-700 rounded-lg px-3 py-2 text-sm hover:bg-blue-100"
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ClarificationCard;

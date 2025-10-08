import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';

interface MarkdownProps {
  content: string;
  className?: string;
}

export default function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          p: ({ children }: any) => <p className="leading-7 text-gray-800 whitespace-pre-wrap">{children}</p>,
          ul: ({ children }: any) => <ul className="list-disc list-inside space-y-1 text-gray-800">{children}</ul>,
          ol: ({ children }: any) => <ol className="list-decimal list-inside space-y-1 text-gray-800">{children}</ol>,
          li: ({ children }: any) => <li className="leading-6 text-gray-800">{children}</li>,
          a: ({ href, children }: any) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-green-600 underline">{children}</a>,
          code: ({ inline, children }: any) =>
            inline ? (
              <code className="px-1 py-0.5 rounded bg-gray-100 text-gray-800 font-mono text-[90%]">{children}</code>
            ) : (
              <pre className="rounded-lg bg-gray-900 text-gray-100 p-3 overflow-auto">
                <code className="font-mono text-[90%]">{children}</code>
              </pre>
            ),
          h1: ({ children }: any) => <h1 className="text-xl font-semibold text-gray-900">{children}</h1>,
          h2: ({ children }: any) => <h2 className="text-lg font-semibold text-gray-900">{children}</h2>,
          h3: ({ children }: any) => <h3 className="text-base font-semibold text-gray-900">{children}</h3>,
          table: ({ children }: any) => <div className="overflow-x-auto"><table className="text-sm text-left">{children}</table></div>,
          th: ({ children }: any) => <th className="px-3 py-2 bg-gray-50 font-medium text-gray-700">{children}</th>,
          td: ({ children }: any) => <td className="px-3 py-2 border-t text-gray-800">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}



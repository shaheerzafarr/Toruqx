'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as Popover from '@radix-ui/react-popover';
import { Message, CitationSource } from '../types';
import { FileText, Award, Calendar, CornerDownRight } from 'lucide-react';

interface ChatMessageBubbleProps {
  message: Message;
}

export default function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isAssistant = message.role === 'assistant';
  const sources = message.sources || [];

  // Parse inline citation brackets (e.g., [1], [2]) and turn them into Markdown anchors (e.g., [1](#citation-1))
  const formatCitations = (text: string) => {
    return text.replace(/\[(\d+)\]/g, '[$1](#citation-$1)');
  };

  // Custom link renderer for ReactMarkdown
  const MarkdownComponents = {
    a: ({ href, children }: any) => {
      const match = href?.match(/^#citation-(\d+)$/);
      if (match) {
        const citationIndex = parseInt(match[1], 10);
        const source = sources[citationIndex - 1];
        
        if (!source) {
          // Fallback if citation index exceeds retrieved sources list
          return <span className="px-1 text-slate-500 font-semibold text-xs bg-slate-900 border border-slate-800 rounded">[{children}]</span>;
        }

        return (
          <Popover.Root>
            <Popover.Trigger asChild>
              <button
                type="button"
                className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-[10px] font-bold text-slate-200 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded transition-all cursor-pointer select-none"
              >
                [{children}]
              </button>
            </Popover.Trigger>
            
            <Popover.Portal>
              <Popover.Content
                side="top"
                align="center"
                sideOffset={6}
                className="w-80 max-w-sm bg-slate-950/95 border border-slate-800 text-slate-300 rounded-xl p-4 shadow-2xl z-50 animate-in fade-in slide-in-from-bottom-2 duration-200 backdrop-blur-md"
              >
                {/* Popover Header */}
                <div className="flex items-start justify-between gap-3 mb-2 border-b border-slate-900 pb-2">
                  <div className="flex items-center gap-2 text-slate-200">
                    <FileText className="h-4 w-4 text-blue-400 shrink-0" />
                    <span className="text-xs font-bold truncate max-w-[180px]" title={source.filename}>
                      {source.filename}
                    </span>
                  </div>
                  <div className="flex items-center gap-1 text-[10px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-semibold">
                    <Award className="h-3 w-3 text-emerald-400" />
                    <span>{Math.round(source.score * 100)}% Match</span>
                  </div>
                </div>

                {/* Citation Context Content */}
                <div className="space-y-2">
                  <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider flex items-center gap-1">
                    <CornerDownRight className="h-3 w-3" />
                    <span>Context Segment (Chunk {source.chunk_index})</span>
                  </div>
                  <div className="text-xs text-slate-400 bg-slate-900/40 p-2.5 rounded-lg border border-slate-900 max-h-40 overflow-y-auto leading-relaxed italic">
                    "{source.text}"
                  </div>
                </div>

                <Popover.Arrow className="fill-slate-950 stroke-slate-800 stroke-1" />
              </Popover.Content>
            </Popover.Portal>
          </Popover.Root>
        );
      }

      return (
        <a 
          href={href} 
          target="_blank" 
          rel="noopener noreferrer" 
          className="text-blue-400 hover:underline transition-colors"
        >
          {children}
        </a>
      );
    },
    // Customize code block rendering inside chat bubble
    code: ({ node, inline, className, children, ...props }: any) => {
      const match = /language-(\w+)/.exec(className || '');
      return !inline ? (
        <pre className="bg-slate-950 border border-slate-900 p-4 rounded-xl overflow-x-auto my-3 text-xs font-mono text-slate-300">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      ) : (
        <code className="bg-slate-900 text-slate-200 px-1.5 py-0.5 rounded text-xs font-mono border border-slate-800" {...props}>
          {children}
        </code>
      );
    }
  };

  // Convert ISO string to user-friendly local time
  const formattedTime = new Date(message.created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`flex items-start gap-4 ${isAssistant ? 'justify-start' : 'justify-end'} mb-6 group`}>
      {/* Assistant Avatar Icon */}
      {isAssistant && (
        <div className="p-2.5 bg-slate-900 border border-slate-800 text-slate-300 rounded-xl shrink-0">
          <FileText className="h-4.5 w-4.5 text-blue-400" />
        </div>
      )}

      {/* Chat Bubble Body */}
      <div className="flex flex-col max-w-[85%] sm:max-w-[70%]">
        <div
          className={`px-4 py-3 rounded-2xl border ${
            isAssistant
              ? 'bg-slate-900/20 text-slate-300 border-slate-900/80 rounded-tl-none'
              : 'bg-slate-100 text-slate-950 border-transparent rounded-tr-none shadow-md'
          }`}
        >
          <div className="text-sm leading-relaxed select-text prose prose-invert max-w-none break-words">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={MarkdownComponents}
            >
              {isAssistant ? formatCitations(message.content) : message.content}
            </ReactMarkdown>
          </div>
        </div>

        {/* Timestamp Footer */}
        <span 
          className={`text-[10px] text-slate-500 font-semibold mt-1 px-1.5 flex items-center gap-1 ${
            isAssistant ? 'justify-start' : 'justify-end'
          }`}
        >
          <Calendar className="h-3 w-3 shrink-0" />
          {formattedTime}
        </span>
      </div>

      {/* User Avatar Icon */}
      {!isAssistant && (
        <div className="p-2.5 bg-slate-100 text-slate-950 rounded-xl shrink-0">
          <UserIcon className="h-4.5 w-4.5" />
        </div>
      )}
    </div>
  );
}

// Simple fallback user icon to avoid Radix avatar loads
function UserIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

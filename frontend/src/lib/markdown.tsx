"use client"

import React from "react"
import Markdown from "react-markdown"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import rehypeHighlight from "rehype-highlight"

interface MarkdownContentProps {
  content: string
  className?: string
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div className={className}>
      <Markdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={{
          pre({ children, ...props }) {
            return (
              <pre
                className="overflow-x-auto rounded-md bg-muted/50 p-3 text-sm"
                {...props}
              >
                {children}
              </pre>
            )
          },
          code({ children, className: codeClassName, ...props }) {
            const isInline = !codeClassName
            if (isInline) {
              return (
                <code
                  className="rounded bg-muted/50 px-1.5 py-0.5 text-sm"
                  {...props}
                >
                  {children}
                </code>
              )
            }
            return (
              <code className={codeClassName} {...props}>
                {children}
              </code>
            )
          },
          p({ children, ...props }) {
            return (
              <p className="mb-2 last:mb-0 leading-relaxed" {...props}>
                {children}
              </p>
            )
          },
          ul({ children, ...props }) {
            return (
              <ul className="mb-2 list-disc pl-6 last:mb-0" {...props}>
                {children}
              </ul>
            )
          },
          ol({ children, ...props }) {
            return (
              <ol className="mb-2 list-decimal pl-6 last:mb-0" {...props}>
                {children}
              </ol>
            )
          },
          li({ children, ...props }) {
            return (
              <li className="mb-1" {...props}>
                {children}
              </li>
            )
          },
          h1({ children, ...props }) {
            return (
              <h1 className="mb-3 text-xl font-bold" {...props}>
                {children}
              </h1>
            )
          },
          h2({ children, ...props }) {
            return (
              <h2 className="mb-2 text-lg font-semibold" {...props}>
                {children}
              </h2>
            )
          },
          h3({ children, ...props }) {
            return (
              <h3 className="mb-2 text-base font-semibold" {...props}>
                {children}
              </h3>
            )
          },
          table({ children, ...props }) {
            return (
              <div className="mb-2 overflow-x-auto">
                <table
                  className="w-full border-collapse text-sm"
                  {...props}
                >
                  {children}
                </table>
              </div>
            )
          },
          th({ children, ...props }) {
            return (
              <th
                className="border border-border px-3 py-1.5 text-left font-semibold bg-muted/30"
                {...props}
              >
                {children}
              </th>
            )
          },
          td({ children, ...props }) {
            return (
              <td className="border border-border px-3 py-1.5" {...props}>
                {children}
              </td>
            )
          },
          blockquote({ children, ...props }) {
            return (
              <blockquote
                className="mb-2 border-l-2 border-primary/40 pl-4 italic text-muted-foreground"
                {...props}
              >
                {children}
              </blockquote>
            )
          },
          hr(props) {
            return <hr className="my-4 border-border" {...props} />
          },
        }}
      >
        {content}
      </Markdown>
    </div>
  )
}

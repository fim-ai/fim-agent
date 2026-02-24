"use client"

import { useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

type AgentMode = "react" | "dag"
type Language = "en" | "zh"

interface ExamplesProps {
  mode: AgentMode
  language: Language
  onLanguageChange: (lang: Language) => void
  onSelect: (query: string) => void
  disabled?: boolean
}

const EXAMPLES: Record<AgentMode, Record<Language, string[]>> = {
  react: {
    en: [
      "Simulate the Monty Hall problem 10,000 times \u2014 should you switch doors? Show the win rates",
      "Simulate the Birthday Paradox: how often do 2 of 23 people share a birthday? Run 10,000 trials",
      "Estimate pi by throwing 1,000,000 random darts at a unit square \u2014 how close can you get?",
      "Solve the 8-queens puzzle: place 8 queens on a chessboard so none attack each other. How many solutions exist?",
      "Generate a random 15x15 maze and solve it with BFS, show the maze and solution path as ASCII art",
      "Find all Pythagorean triples (a\u00b2 + b\u00b2 = c\u00b2) where c < 100. How many are there?",
      "Simulate 5,000 hands of Blackjack with basic strategy (hit below 17) \u2014 what's the player win rate?",
      "Crack this Caesar cipher: 'Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj' \u2014 try all 26 shifts, score by English letter frequency",
    ],
    zh: [
      "\u6a21\u62df\u8499\u63d0\u970d\u5c14\u95ee\u9898 10,000 \u6b21\u2014\u2014\u5e94\u8be5\u6362\u95e8\u5417\uff1f\u5c55\u793a\u80dc\u7387\u7edf\u8ba1",
      "\u6a21\u62df\u751f\u65e5\u6096\u8bba\uff1a23 \u4e2a\u4eba\u4e2d\u6709 2 \u4eba\u540c\u4e00\u5929\u751f\u65e5\u7684\u6982\u7387\u662f\u591a\u5c11\uff1f\u6a21\u62df 10,000 \u6b21",
      "\u7528\u8499\u7279\u5361\u6d1b\u65b9\u6cd5\u4f30\u7b97\u5706\u5468\u7387\uff1a\u5f80\u5355\u4f4d\u6b63\u65b9\u5f62\u4e0a\u6295 1,000,000 \u4e2a\u968f\u673a\u98de\u9556\uff0c\u80fd\u591a\u63a5\u8fd1\u771f\u5b9e\u503c\uff1f",
      "\u89e3\u516b\u7687\u540e\u95ee\u9898\uff1a\u5728\u68cb\u76d8\u4e0a\u653e 8 \u4e2a\u7687\u540e\u4f7f\u5176\u4e92\u4e0d\u653b\u51fb\uff0c\u4e00\u5171\u6709\u591a\u5c11\u79cd\u89e3\u6cd5\uff1f",
      "\u968f\u673a\u751f\u6210\u4e00\u4e2a 15x15 \u8ff7\u5bab\u5e76\u7528 BFS \u6c42\u89e3\uff0c\u7528 ASCII \u5b57\u7b26\u753b\u5c55\u793a\u8ff7\u5bab\u548c\u8def\u5f84",
      "\u627e\u51fa\u6240\u6709 c < 100 \u7684\u52fe\u80a1\u6570 (a\u00b2 + b\u00b2 = c\u00b2)\uff0c\u4e00\u5171\u6709\u591a\u5c11\u7ec4\uff1f",
      "\u6a21\u62df 5,000 \u5c40 21 \u70b9\uff0c\u4f7f\u7528\u57fa\u672c\u7b56\u7565\uff08\u4f4e\u4e8e 17 \u5c31\u8981\u724c\uff09\u2014\u2014\u73a9\u5bb6\u80dc\u7387\u662f\u591a\u5c11\uff1f",
      "\u7834\u89e3\u51ef\u6492\u5bc6\u7801\uff1a'Wkh txlfn eurzq ira mxpsv ryhu wkh odcb grj'\u2014\u2014\u5c1d\u8bd5\u6240\u6709 26 \u79cd\u4f4d\u79fb\uff0c\u7528\u82f1\u8bed\u5b57\u6bcd\u9891\u7387\u8bc4\u5206",
    ],
  },
  dag: {
    en: [
      "Implement bubble sort AND quicksort separately, benchmark both on a 10,000-element random list, then compare their speeds",
      "Implement linear search AND binary search, race both finding 1,000 random targets in a sorted 100,000-element list, then compare total operations",
      "Simulate 10,000 Monty Hall rounds with always-switch AND 10,000 with always-stay, then compare win rates and explain the paradox",
      "Simulate Martingale betting AND flat-bet strategy over 500 coin flips starting with $1,000 each, then compare who survived longer",
      "Estimate pi via Monte Carlo (1M darts) AND via the Leibniz series (1M terms), then compare which method is more accurate",
      "Compute the first 50 Fibonacci numbers AND the first 50 primes, then find which numbers appear in both sequences",
      "Write a Caesar cipher encoder AND a brute-force decoder, encode 'ATTACK AT DAWN' with a random shift, then crack it with the decoder",
      "Generate a random 20x20 maze, then solve it using BFS AND DFS in parallel, compare which algorithm explored fewer cells",
    ],
    zh: [
      "\u5206\u522b\u5b9e\u73b0\u5192\u6ce1\u6392\u5e8f\u548c\u5feb\u901f\u6392\u5e8f\uff0c\u5728 10,000 \u4e2a\u968f\u673a\u5143\u7d20\u4e0a\u8dd1\u57fa\u51c6\u6d4b\u8bd5\uff0c\u7136\u540e\u5bf9\u6bd4\u4e24\u8005\u901f\u5ea6",
      "\u5206\u522b\u5b9e\u73b0\u7ebf\u6027\u641c\u7d22\u548c\u4e8c\u5206\u641c\u7d22\uff0c\u5728 100,000 \u4e2a\u6709\u5e8f\u5143\u7d20\u4e2d\u641c\u7d22 1,000 \u4e2a\u968f\u673a\u76ee\u6807\uff0c\u7136\u540e\u5bf9\u6bd4\u603b\u64cd\u4f5c\u6b21\u6570",
      "\u6a21\u62df\u8499\u63d0\u970d\u5c14\u95ee\u9898\uff1a\u59cb\u7ec8\u6362\u95e8 10,000 \u6b21 vs \u59cb\u7ec8\u4e0d\u6362 10,000 \u6b21\uff0c\u5bf9\u6bd4\u80dc\u7387\u5e76\u89e3\u91ca\u6096\u8bba",
      "\u6a21\u62df\u9a6c\u4e01\u683c\u5c14\u7b56\u7565\u548c\u5e73\u6ce8\u7b56\u7565\u5404\u8fdb\u884c 500 \u6b21\u629b\u786c\u5e01\uff08\u8d77\u59cb $1,000\uff09\uff0c\u5bf9\u6bd4\u8c01\u6d3b\u5f97\u66f4\u4e45",
      "\u7528\u8499\u7279\u5361\u6d1b\u6cd5\uff08100 \u4e07\u98de\u9556\uff09\u548c\u83b1\u5e03\u5c3c\u8328\u7ea7\u6570\uff08100 \u4e07\u9879\uff09\u5206\u522b\u4f30\u7b97\u5706\u5468\u7387\uff0c\u5bf9\u6bd4\u54ea\u79cd\u65b9\u6cd5\u66f4\u7cbe\u786e",
      "\u8ba1\u7b97\u524d 50 \u4e2a\u6590\u6ce2\u90a3\u5951\u6570\u548c\u524d 50 \u4e2a\u7d20\u6570\uff0c\u7136\u540e\u627e\u51fa\u540c\u65f6\u51fa\u73b0\u5728\u4e24\u4e2a\u5e8f\u5217\u4e2d\u7684\u6570",
      "\u7f16\u5199\u51ef\u6492\u5bc6\u7801\u52a0\u5bc6\u5668\u548c\u66b4\u529b\u7834\u89e3\u5668\uff0c\u7528\u968f\u673a\u4f4d\u79fb\u52a0\u5bc6 'ATTACK AT DAWN'\uff0c\u518d\u7528\u7834\u89e3\u5668\u7834\u89e3",
      "\u968f\u673a\u751f\u6210 20x20 \u8ff7\u5bab\uff0c\u7136\u540e\u7528 BFS \u548c DFS \u5e76\u884c\u6c42\u89e3\uff0c\u5bf9\u6bd4\u54ea\u79cd\u7b97\u6cd5\u63a2\u7d22\u7684\u683c\u5b50\u66f4\u5c11",
    ],
  },
}

export function Examples({
  mode,
  language,
  onLanguageChange,
  onSelect,
  disabled,
}: ExamplesProps) {
  const examples = EXAMPLES[mode][language]

  const handleSelect = useCallback(
    (query: string) => {
      if (!disabled) {
        onSelect(query)
      }
    },
    [disabled, onSelect]
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Examples
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant={language === "en" ? "secondary" : "ghost"}
            size="xs"
            onClick={() => onLanguageChange("en")}
            className="text-xs"
          >
            EN
          </Button>
          <Button
            variant={language === "zh" ? "secondary" : "ghost"}
            size="xs"
            onClick={() => onLanguageChange("zh")}
            className="text-xs"
          >
            中文
          </Button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {examples.map((example, i) => (
          <Badge
            key={i}
            variant="outline"
            className={
              "cursor-pointer text-xs font-normal transition-colors hover:bg-accent hover:text-accent-foreground max-w-full" +
              (disabled ? " opacity-50 pointer-events-none" : "")
            }
            onClick={() => handleSelect(example)}
          >
            <span className="truncate">{example}</span>
          </Badge>
        ))}
      </div>
    </div>
  )
}

export type { AgentMode, Language }

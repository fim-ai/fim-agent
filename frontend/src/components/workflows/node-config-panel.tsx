"use client"

import { useCallback } from "react"
import { useTranslations } from "next-intl"
import { Plus, Trash2, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Node } from "@xyflow/react"
import type { WorkflowNodeType } from "@/types/workflow"

interface NodeConfigPanelProps {
  node: Node | null
  onUpdate: (nodeId: string, data: Record<string, unknown>) => void
  onClose: () => void
}

export function NodeConfigPanel({ node, onUpdate, onClose }: NodeConfigPanelProps) {
  const t = useTranslations("workflows")

  const updateField = useCallback(
    (field: string, value: unknown) => {
      if (!node) return
      onUpdate(node.id, { ...node.data, [field]: value })
    },
    [node, onUpdate],
  )

  if (!node) {
    return (
      <div className="flex flex-col h-full border-l border-border/40 bg-background w-[300px]">
        <div className="flex items-center justify-center h-full">
          <p className="text-xs text-muted-foreground">{t("configNoSelection")}</p>
        </div>
      </div>
    )
  }

  const nodeType = node.type as WorkflowNodeType

  return (
    <div className="flex flex-col h-full border-l border-border/40 bg-background w-[300px]">
      <div className="flex items-center justify-between px-3 pt-3 pb-2 shrink-0 border-b border-border/40">
        <h3 className="text-xs font-semibold text-foreground">
          {t("configTitle")}
        </h3>
        <Button variant="ghost" size="icon-sm" onClick={onClose}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-4">
          <p className="text-sm font-medium text-foreground">
            {t(`nodeType_${nodeType}` as Parameters<typeof t>[0])}
          </p>
          <NodeConfigFields
            nodeType={nodeType}
            data={node.data as Record<string, unknown>}
            updateField={updateField}
          />
        </div>
      </ScrollArea>
    </div>
  )
}

interface NodeConfigFieldsProps {
  nodeType: WorkflowNodeType
  data: Record<string, unknown>
  updateField: (field: string, value: unknown) => void
}

function NodeConfigFields({ nodeType, data, updateField }: NodeConfigFieldsProps) {
  const t = useTranslations("workflows")

  switch (nodeType) {
    case "start":
      return <StartConfig data={data} updateField={updateField} t={t} />
    case "end":
      return <EndConfig data={data} updateField={updateField} t={t} />
    case "llm":
      return <LLMConfig data={data} updateField={updateField} t={t} />
    case "conditionBranch":
      return <ConditionConfig data={data} updateField={updateField} t={t} />
    case "questionClassifier":
      return <QuestionClassifierConfig data={data} updateField={updateField} t={t} />
    case "agent":
      return <AgentConfig data={data} updateField={updateField} t={t} />
    case "knowledgeRetrieval":
      return <KnowledgeRetrievalConfig data={data} updateField={updateField} t={t} />
    case "connector":
      return <ConnectorConfig data={data} updateField={updateField} t={t} />
    case "httpRequest":
      return <HTTPRequestConfig data={data} updateField={updateField} t={t} />
    case "variableAssign":
      return <VariableAssignConfig data={data} updateField={updateField} t={t} />
    case "templateTransform":
      return <TemplateTransformConfig data={data} updateField={updateField} t={t} />
    case "codeExecution":
      return <CodeExecutionConfig data={data} updateField={updateField} t={t} />
    default:
      return <p className="text-xs text-muted-foreground">No configuration available</p>
  }
}

type ConfigProps = {
  data: Record<string, unknown>
  updateField: (field: string, value: unknown) => void
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  t: any
}

function StartConfig({ data, updateField, t }: ConfigProps) {
  const variables = (data.variables ?? []) as Array<{ name: string; type: string; default_value?: string; required?: boolean }>

  const addVariable = () => {
    updateField("variables", [...variables, { name: "", type: "string", required: false }])
  }

  const removeVariable = (idx: number) => {
    updateField("variables", variables.filter((_, i) => i !== idx))
  }

  const updateVariable = (idx: number, field: string, value: unknown) => {
    const updated = variables.map((v, i) => (i === idx ? { ...v, [field]: value } : v))
    updateField("variables", updated)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium">{t("configVariables")}</label>
        <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={addVariable}>
          <Plus className="h-3 w-3" />
          {t("configAddVariable")}
        </Button>
      </div>
      {variables.map((v, i) => (
        <div key={i} className="space-y-2 rounded-md border border-border p-2">
          <div className="flex items-center gap-2">
            <Input
              className="h-7 text-xs flex-1"
              placeholder={t("configVariableName")}
              value={v.name}
              onChange={(e) => updateVariable(i, "name", e.target.value)}
            />
            <Button variant="ghost" size="icon-sm" onClick={() => removeVariable(i)}>
              <Trash2 className="h-3 w-3 text-destructive" />
            </Button>
          </div>
          <Select value={v.type} onValueChange={(val) => updateVariable(i, "type", val)}>
            <SelectTrigger className="w-full h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="string">String</SelectItem>
              <SelectItem value="number">Number</SelectItem>
              <SelectItem value="boolean">Boolean</SelectItem>
              <SelectItem value="object">Object</SelectItem>
              <SelectItem value="array">Array</SelectItem>
            </SelectContent>
          </Select>
          <Input
            className="h-7 text-xs"
            placeholder={t("configVariableDefault")}
            value={v.default_value ?? ""}
            onChange={(e) => updateVariable(i, "default_value", e.target.value)}
          />
          <div className="flex items-center justify-between">
            <label className="text-[10px] text-muted-foreground">{t("configVariableRequired")}</label>
            <Switch
              checked={v.required ?? false}
              onCheckedChange={(checked) => updateVariable(i, "required", checked)}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function EndConfig({ data, updateField, t }: ConfigProps) {
  const mapping = (data.output_mapping ?? {}) as Record<string, string>
  const entries = Object.entries(mapping)

  const addMapping = () => {
    updateField("output_mapping", { ...mapping, "": "" })
  }

  const removeMapping = (key: string) => {
    const updated = { ...mapping }
    delete updated[key]
    updateField("output_mapping", updated)
  }

  const updateMapping = (oldKey: string, newKey: string, value: string) => {
    const updated: Record<string, string> = {}
    for (const [k, v] of Object.entries(mapping)) {
      if (k === oldKey) {
        updated[newKey] = value
      } else {
        updated[k] = v
      }
    }
    updateField("output_mapping", updated)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium">{t("configOutputMapping")}</label>
        <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={addMapping}>
          <Plus className="h-3 w-3" />
          {t("configAddMapping")}
        </Button>
      </div>
      {entries.map(([key, value], i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            className="h-7 text-xs flex-1"
            placeholder={t("configKey")}
            value={key}
            onChange={(e) => updateMapping(key, e.target.value, value)}
          />
          <Input
            className="h-7 text-xs flex-1"
            placeholder={t("configValue")}
            value={value}
            onChange={(e) => updateMapping(key, key, e.target.value)}
          />
          <Button variant="ghost" size="icon-sm" onClick={() => removeMapping(key)}>
            <Trash2 className="h-3 w-3 text-destructive" />
          </Button>
        </div>
      ))}
    </div>
  )
}

function LLMConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configModel")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="gpt-4o"
          value={(data.model ?? "") as string}
          onChange={(e) => updateField("model", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configPromptTemplate")}</label>
        <Textarea
          className="text-xs resize-none"
          rows={4}
          placeholder={t("configPromptHint")}
          value={(data.prompt_template ?? "") as string}
          onChange={(e) => updateField("prompt_template", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="result"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configTemperature")}: {((data.temperature ?? 0.7) as number).toFixed(1)}</label>
        <Slider
          value={[(data.temperature ?? 0.7) as number]}
          onValueChange={([v]) => updateField("temperature", v)}
          min={0}
          max={2}
          step={0.1}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configMaxTokens")}</label>
        <Input
          className="h-7 text-xs"
          type="number"
          placeholder="4096"
          value={(data.max_tokens ?? "") as string}
          onChange={(e) => updateField("max_tokens", e.target.value ? Number(e.target.value) : undefined)}
        />
      </div>
    </div>
  )
}

function ConditionConfig({ data, updateField, t }: ConfigProps) {
  const mode = (data.mode ?? "expression") as string
  const conditions = (data.conditions ?? []) as Array<{ id: string; label: string; expression?: string; llm_prompt?: string }>

  const addCondition = () => {
    const newId = `cond_${Date.now()}`
    updateField("conditions", [...conditions, { id: newId, label: "" }])
  }

  const removeCondition = (idx: number) => {
    updateField("conditions", conditions.filter((_, i) => i !== idx))
  }

  const updateCondition = (idx: number, field: string, value: unknown) => {
    const updated = conditions.map((c, i) => (i === idx ? { ...c, [field]: value } : c))
    updateField("conditions", updated)
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configMode")}</label>
        <Select value={mode} onValueChange={(v) => updateField("mode", v)}>
          <SelectTrigger className="w-full h-7 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="expression">{t("configModeExpression")}</SelectItem>
            <SelectItem value="llm">{t("configModeLLM")}</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium">{t("configConditions")}</label>
        <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={addCondition}>
          <Plus className="h-3 w-3" />
          {t("configAddCondition")}
        </Button>
      </div>
      {conditions.map((c, i) => (
        <div key={c.id ?? i} className="space-y-2 rounded-md border border-border p-2">
          <div className="flex items-center gap-2">
            <Input
              className="h-7 text-xs flex-1"
              placeholder={t("configConditionLabel")}
              value={c.label}
              onChange={(e) => updateCondition(i, "label", e.target.value)}
            />
            <Button variant="ghost" size="icon-sm" onClick={() => removeCondition(i)}>
              <Trash2 className="h-3 w-3 text-destructive" />
            </Button>
          </div>
          {mode === "expression" ? (
            <Input
              className="h-7 text-xs"
              placeholder={t("configExpression")}
              value={c.expression ?? ""}
              onChange={(e) => updateCondition(i, "expression", e.target.value)}
            />
          ) : (
            <Textarea
              className="text-xs resize-none"
              rows={2}
              placeholder={t("configLLMPrompt")}
              value={c.llm_prompt ?? ""}
              onChange={(e) => updateCondition(i, "llm_prompt", e.target.value)}
            />
          )}
        </div>
      ))}
    </div>
  )
}

function QuestionClassifierConfig({ data, updateField, t }: ConfigProps) {
  const classes = (data.classes ?? []) as Array<{ id: string; label: string; description?: string }>

  const addClass = () => {
    const newId = `cls_${Date.now()}`
    updateField("classes", [...classes, { id: newId, label: "" }])
  }

  const removeClass = (idx: number) => {
    updateField("classes", classes.filter((_, i) => i !== idx))
  }

  const updateClass = (idx: number, field: string, value: unknown) => {
    const updated = classes.map((c, i) => (i === idx ? { ...c, [field]: value } : c))
    updateField("classes", updated)
  }

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configModel")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="gpt-4o"
          value={(data.model ?? "") as string}
          onChange={(e) => updateField("model", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configPromptTemplate")}</label>
        <Textarea
          className="text-xs resize-none"
          rows={3}
          value={(data.prompt ?? "") as string}
          onChange={(e) => updateField("prompt", e.target.value)}
        />
      </div>
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium">{t("configClasses")}</label>
        <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={addClass}>
          <Plus className="h-3 w-3" />
          {t("configAddClass")}
        </Button>
      </div>
      {classes.map((c, i) => (
        <div key={c.id ?? i} className="space-y-2 rounded-md border border-border p-2">
          <div className="flex items-center gap-2">
            <Input
              className="h-7 text-xs flex-1"
              placeholder={t("configClassLabel")}
              value={c.label}
              onChange={(e) => updateClass(i, "label", e.target.value)}
            />
            <Button variant="ghost" size="icon-sm" onClick={() => removeClass(i)}>
              <Trash2 className="h-3 w-3 text-destructive" />
            </Button>
          </div>
          <Input
            className="h-7 text-xs"
            placeholder={t("configClassDescription")}
            value={c.description ?? ""}
            onChange={(e) => updateClass(i, "description", e.target.value)}
          />
        </div>
      ))}
    </div>
  )
}

function AgentConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configSelectAgent")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="Agent ID"
          value={(data.agent_id ?? "") as string}
          onChange={(e) => updateField("agent_id", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configPromptTemplate")}</label>
        <Textarea
          className="text-xs resize-none"
          rows={3}
          placeholder={t("configPromptHint")}
          value={(data.prompt_template ?? "") as string}
          onChange={(e) => updateField("prompt_template", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="result"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
    </div>
  )
}

function KnowledgeRetrievalConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configSelectKB")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="KB ID"
          value={(data.kb_id ?? "") as string}
          onChange={(e) => updateField("kb_id", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configQueryTemplate")}</label>
        <Textarea
          className="text-xs resize-none"
          rows={3}
          placeholder={t("configPromptHint")}
          value={(data.query_template ?? "") as string}
          onChange={(e) => updateField("query_template", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configTopK")}</label>
        <Input
          className="h-7 text-xs"
          type="number"
          placeholder="5"
          value={(data.top_k ?? "") as string}
          onChange={(e) => updateField("top_k", e.target.value ? Number(e.target.value) : undefined)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="result"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
    </div>
  )
}

function ConnectorConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configSelectConnector")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="Connector ID"
          value={(data.connector_id ?? "") as string}
          onChange={(e) => updateField("connector_id", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configSelectAction")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="Action name"
          value={(data.action ?? "") as string}
          onChange={(e) => updateField("action", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="result"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
    </div>
  )
}

function HTTPRequestConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configMethod")}</label>
        <Select value={(data.method ?? "GET") as string} onValueChange={(v) => updateField("method", v)}>
          <SelectTrigger className="w-full h-7 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="GET">GET</SelectItem>
            <SelectItem value="POST">POST</SelectItem>
            <SelectItem value="PUT">PUT</SelectItem>
            <SelectItem value="PATCH">PATCH</SelectItem>
            <SelectItem value="DELETE">DELETE</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configURL")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="https://api.example.com/..."
          value={(data.url ?? "") as string}
          onChange={(e) => updateField("url", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configBody")}</label>
        <Textarea
          className="text-xs resize-none font-mono"
          rows={3}
          placeholder="{}"
          value={(data.body ?? "") as string}
          onChange={(e) => updateField("body", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="response"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
    </div>
  )
}

function VariableAssignConfig({ data, updateField, t }: ConfigProps) {
  const assignments = (data.assignments ?? []) as Array<{ variable: string; expression: string }>

  const addAssignment = () => {
    updateField("assignments", [...assignments, { variable: "", expression: "" }])
  }

  const removeAssignment = (idx: number) => {
    updateField("assignments", assignments.filter((_, i) => i !== idx))
  }

  const updateAssignment = (idx: number, field: string, value: string) => {
    const updated = assignments.map((a, i) => (i === idx ? { ...a, [field]: value } : a))
    updateField("assignments", updated)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium">{t("configAssignments")}</label>
        <Button variant="ghost" size="sm" className="h-6 text-xs gap-1" onClick={addAssignment}>
          <Plus className="h-3 w-3" />
          {t("configAddAssignment")}
        </Button>
      </div>
      {assignments.map((a, i) => (
        <div key={i} className="flex items-center gap-2">
          <Input
            className="h-7 text-xs flex-1"
            placeholder={t("configVariable")}
            value={a.variable}
            onChange={(e) => updateAssignment(i, "variable", e.target.value)}
          />
          <Input
            className="h-7 text-xs flex-1"
            placeholder={t("configExpression")}
            value={a.expression}
            onChange={(e) => updateAssignment(i, "expression", e.target.value)}
          />
          <Button variant="ghost" size="icon-sm" onClick={() => removeAssignment(i)}>
            <Trash2 className="h-3 w-3 text-destructive" />
          </Button>
        </div>
      ))}
    </div>
  )
}

function TemplateTransformConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configTemplate")}</label>
        <Textarea
          className="text-xs resize-none font-mono"
          rows={6}
          value={(data.template ?? "") as string}
          onChange={(e) => updateField("template", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="result"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
    </div>
  )
}

function CodeExecutionConfig({ data, updateField, t }: ConfigProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configLanguage")}</label>
        <Select value={(data.language ?? "python") as string} onValueChange={(v) => updateField("language", v)}>
          <SelectTrigger className="w-full h-7 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="python">Python</SelectItem>
            <SelectItem value="javascript">JavaScript</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configCode")}</label>
        <Textarea
          className="text-xs resize-none font-mono"
          rows={8}
          value={(data.code ?? "") as string}
          onChange={(e) => updateField("code", e.target.value)}
        />
      </div>
      <div className="space-y-1.5">
        <label className="text-xs font-medium">{t("configOutputVariable")}</label>
        <Input
          className="h-7 text-xs"
          placeholder="result"
          value={(data.output_variable ?? "") as string}
          onChange={(e) => updateField("output_variable", e.target.value)}
        />
      </div>
    </div>
  )
}

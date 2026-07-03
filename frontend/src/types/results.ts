import type { ReactNode } from 'react'
import type {
  ExecutionFailure,
  ExecutionStep,
  PlannerMetadata,
  PlanStep,
  RunTestResponse,
} from './api'

export type MissingValueKind = 'detected' | 'captured'

export type RunDisplayVariant = 'pass' | 'issues' | 'failed' | 'error' | 'unknown'

export interface RunDisplayStatus {
  label: string
  variant: RunDisplayVariant
}

export interface PlannerConfidence {
  value: number
  label: string
}

export interface ConfidencePresentation {
  label: string
  badgeClass: string
  barColor: string
}

export interface ExecutionStats {
  actionsExecuted: number
  assertions: number
  navigationEvents: number
  waitTimeMs: number
  retries: number
  selfHealingCount: number
  contextRefreshes: number
  pagesVisited: number
}

export interface ActionPill {
  label: string
  className: string
  icon: IconName
}

export interface CoverageStatus {
  label: string
  className: string
}

export interface AiWebsiteAnalysisView {
  websiteType?: string | null
  businessDomain?: string | null
  primaryGoal?: string | null
  targetAudience?: string | null
  recommendedJourneys?: string[] | null
  highRiskAreas?: string[] | null
  testingStrategy?: string | null
  analysisConfidence?: number | null
  analysisReasoning?: string | null
  contextExtracted: boolean
}

export type IconName =
  | 'copy'
  | 'arrow-right'
  | 'world'
  | 'eye'
  | 'cursor'
  | 'arrows-vertical'
  | 'camera'
  | 'clock'
  | 'check'
  | 'x'
  | 'minus'
  | 'circle-check'
  | 'alert-triangle'
  | 'chevron-down'
  | 'photo-off'

export interface IconProps {
  name: IconName
  size?: number
  className?: string
  style?: React.CSSProperties
  'aria-hidden'?: boolean | 'true' | 'false'
}

export interface SectionHeaderProps {
  title: string
  subtitle?: string
  meta?: ReactNode
}

export interface FailureCardProps {
  failure: ExecutionFailure
  index: number
  totalSteps: number
  stepLabel?: string | null
  stepId?: string | number
}

export interface CollapsibleReasoningProps {
  meta: PlannerMetadata
  strategyReasoning?: string | null
}

export type DisplayFieldValue = ReactNode | string | number

export interface ResultsHelperContext {
  result: RunTestResponse
  planStep?: PlanStep
  execStep?: ExecutionStep
  failure?: ExecutionFailure | null
}

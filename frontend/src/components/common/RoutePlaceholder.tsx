"use client";

import * as React from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { LucideIcon, Sparkles, RefreshCw } from "lucide-react";

export interface RoutePlaceholderProps {
  title: string;
  category: string;
  description: string;
  icon: LucideIcon;
  plannedMilestone: string;
  keyFeatures: string[];
  actionLabel?: string;
  onAction?: () => void;
  children?: React.ReactNode;
}

export function RoutePlaceholder({
  title,
  category,
  description,
  icon: Icon,
  plannedMilestone,
  keyFeatures,
  actionLabel = "Simulate Workflow",
  onAction,
  children,
}: RoutePlaceholderProps) {
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 800);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        breadcrumbs={[
          { label: category },
          { label: title },
        ]}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleRefresh}
              isLoading={isRefreshing}
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1" />
              Refresh
            </Button>
            <Button variant="primary" size="sm" onClick={onAction}>
              <Sparkles className="w-3.5 h-3.5 mr-1" />
              {actionLabel}
            </Button>
          </div>
        }
      />

      {/* Screen Overview & Milestone Badge */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="md:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Icon className="w-4 h-4 text-ember" />
                Screen Specification & Purpose
              </CardTitle>
              <Badge variant="ember" size="sm">
                Target: {plannedMilestone}
              </Badge>
            </div>
            <CardDescription>{description}</CardDescription>
          </CardHeader>
          <CardContent>
            <h4 className="text-xs uppercase font-mono text-zinc-400 font-semibold mb-2">
              Key Planned Capabilities:
            </h4>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-zinc-300">
              {keyFeatures.map((feat, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-ember shrink-0" />
                  <span>{feat}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* Status Sentinel Card */}
        <Card>
          <CardHeader>
            <CardTitle>Architecture Sentinel</CardTitle>
            <CardDescription>Deterministic integration status.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-canvas-border/50">
              <span className="text-zinc-400">Design System:</span>
              <Badge variant="success" size="sm">Ready (M02)</Badge>
            </div>
            <div className="flex items-center justify-between pb-2 border-b border-canvas-border/50">
              <span className="text-zinc-400">Backend API:</span>
              <span className="font-mono text-zinc-300">FastAPI Async</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-zinc-400">14 QA Veto:</span>
              <span className="font-mono text-emerald-400 font-semibold">Active</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Screen Body / Empty State */}
      {children ? (
        children
      ) : (
        <Card>
          <CardContent>
            <EmptyState
              icon={Icon}
              title={`${title} Workspace Ready`}
              description={`The user interface for ${title} is scaffolded in the design system. Business logic and backend workers will be wired in ${plannedMilestone}.`}
              actionLabel={actionLabel}
              onAction={onAction || handleRefresh}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { ShoppingBag, Globe, Building2, Layers, Puzzle } from 'lucide-react'
import { EmptyState } from '@/components/shared/empty-state'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api, orgApi, type MarketItem, type UserOrg } from '@/lib/api'
import { toast } from 'sonner'

const CATEGORY_MAP = {
  solutions: ['all', 'agent', 'skill', 'workflow'],
  components: ['all', 'connector', 'mcp_server'],
} as const

type MarketCategory = keyof typeof CATEGORY_MAP

function MarketContent() {
  const t = useTranslations('market')
  const tc = useTranslations('common')
  const searchParams = useSearchParams()
  const router = useRouter()
  const [items, setItems] = useState<MarketItem[]>([])
  const [loading, setLoading] = useState(true)
  const [subscribing, setSubscribing] = useState<string | null>(null)
  const [orgs, setOrgs] = useState<UserOrg[]>([])

  const scope = searchParams.get('scope') || 'market'
  const category = (searchParams.get('category') || 'solutions') as MarketCategory
  const activeType = searchParams.get('type') || 'all'

  // Load user orgs on mount
  useEffect(() => {
    orgApi.list().then(setOrgs).catch(() => {})
  }, [])

  const fetchMarket = useCallback(async () => {
    setLoading(true)
    try {
      const params: Parameters<typeof api.browseMarket>[0] = {
        page: 1,
        size: 50,
        scope: scope === 'market' ? 'market' : `org:${scope}`,
        category,
      }
      if (activeType !== 'all') params.resource_type = activeType
      const res = await api.browseMarket(params)
      setItems(res?.items ?? [])
    } catch {
      toast.error(tc('error'))
    } finally {
      setLoading(false)
    }
  }, [scope, category, activeType, tc])

  useEffect(() => { fetchMarket() }, [fetchMarket])

  const handleSubscribe = async (item: MarketItem) => {
    setSubscribing(item.id)
    try {
      if (item.is_subscribed) {
        await api.unsubscribeResource({ resource_type: item.resource_type, resource_id: item.id, org_id: item.org_id })
        toast.success(t('unsubscribeSuccess'))
      } else {
        await api.subscribeResource({ resource_type: item.resource_type, resource_id: item.id, org_id: item.org_id })
        toast.success(t('subscribeSuccess'))
      }
      fetchMarket()
    } catch {
      toast.error(tc('error'))
    } finally {
      setSubscribing(null)
    }
  }

  const updateParams = useCallback((updates: Record<string, string | null>) => {
    const params = new URLSearchParams(searchParams.toString())
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === '') {
        params.delete(key)
      } else {
        params.set(key, value)
      }
    }
    const qs = params.toString()
    router.replace(qs ? `?${qs}` : '?')
  }, [searchParams, router])

  const handleScopeChange = (newScope: string) => {
    // Keep category, reset type to 'all'
    updateParams({
      scope: newScope === 'market' ? null : newScope,
      type: null,
    })
  }

  const handleCategoryChange = (newCategory: MarketCategory) => {
    // Reset type to 'all' when category changes
    updateParams({
      category: newCategory === 'solutions' ? null : newCategory,
      type: null,
    })
  }

  const handleTypeChange = (type: string) => {
    updateParams({
      type: type === 'all' ? null : type,
    })
  }

  const validCategory = category in CATEGORY_MAP ? category : 'solutions'
  const typeOptions = CATEGORY_MAP[validCategory]

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 shrink-0 border-b border-border/40">
        <div>
          <h1 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <ShoppingBag className="h-5 w-5" />
            {t('title')}
          </h1>
          <p className="text-sm text-muted-foreground">{t('description')}</p>
        </div>
        {/* Scope selector — right side of header */}
        <Select value={scope} onValueChange={handleScopeChange}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="market">
              <span className="flex items-center gap-2">
                <Globe className="h-4 w-4" />
                {t('scopeGlobalMarket')}
              </span>
            </SelectItem>
            {orgs.map((org) => (
              <SelectItem key={org.id} value={org.id}>
                <span className="flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  {org.name}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Category + type filters */}
        <div className="flex items-center gap-3">
          <Tabs value={validCategory} onValueChange={(v) => handleCategoryChange(v as MarketCategory)}>
            <TabsList>
              <TabsTrigger value="solutions" className="gap-1.5">
                <Layers className="h-3.5 w-3.5" />
                {t('categorySolutions')}
              </TabsTrigger>
              <TabsTrigger value="components" className="gap-1.5">
                <Puzzle className="h-3.5 w-3.5" />
                {t('categoryComponents')}
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <Tabs value={activeType} onValueChange={handleTypeChange}>
            <TabsList>
              {typeOptions.map(type => (
                <TabsTrigger key={type} value={type}>
                  {t(`types.${type}`)}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
        </div>

        {loading ? (
          <div className="text-center py-12 text-muted-foreground">{tc('loading')}</div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<ShoppingBag />}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <div key={item.id} className="border rounded-lg p-4 space-y-3 bg-card">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium truncate">{item.name}</h3>
                    {item.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-1">
                        {item.description}
                      </p>
                    )}
                  </div>
                  <Badge variant="secondary" className="shrink-0 text-xs">
                    {t(`types.${item.resource_type}`)}
                  </Badge>
                </div>

                {(item.owner_username || item.org_name) && (
                  <p className="text-xs text-muted-foreground">
                    {item.owner_username}{item.org_name ? ` / ${item.org_name}` : ''}
                  </p>
                )}

                <div className="flex items-center justify-between">
                  {item.is_subscribed && (
                    <Badge variant="outline" className="text-xs">{t('subscribed')}</Badge>
                  )}
                  <Button
                    size="sm"
                    variant={item.is_subscribed ? 'outline' : 'default'}
                    disabled={subscribing === item.id}
                    onClick={() => handleSubscribe(item)}
                    className="ml-auto"
                  >
                    {item.is_subscribed ? t('unsubscribe') : t('subscribe')}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function MarketPage() {
  return (
    <Suspense>
      <MarketContent />
    </Suspense>
  )
}

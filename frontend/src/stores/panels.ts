import { defineStore } from 'pinia'
import type { FunctionalComponent } from 'vue'
import {
  LayoutDashboard,
  Users as UsersIcon,
  ClipboardList,
  FileText,
  FilePlus2,
  BookOpen,
  GraduationCap,
  Settings,
  BarChart3,
  Wallet,
  Building2,
  Layers,
  School,
  ScrollText,
  CreditCard,
  Shield,
  Globe,
  MapPin,
  MapPinned,
  Award,
  Library,
  Inbox,
  LayoutGrid,
} from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

/** Tones map to a coloured rounded icon tile next to the leaf label. */
export type NavTone =
  | 'violet' | 'indigo' | 'sky' | 'cyan' | 'emerald' | 'teal'
  | 'amber' | 'orange' | 'rose' | 'pink' | 'slate'

export interface NavLeaf {
  type: 'leaf'
  to: string
  label: string
  icon: FunctionalComponent
  tone?: NavTone
  rootOnly?: boolean
}

export interface NavGroup {
  type: 'group'
  key: string
  label: string
  icon: FunctionalComponent
  items: NavLeaf[]
  rootOnly?: boolean
}

export type NavEntry = NavLeaf | NavGroup

interface NavOpts { rootOnly?: boolean }

const leaf = (to: string, label: string, icon: any, tone: NavTone = 'slate', opts: NavOpts = {}): NavLeaf =>
  ({ type: 'leaf', to, label, icon, tone, ...opts })

const group = (key: string, label: string, icon: any, items: NavLeaf[], opts: NavOpts = {}): NavGroup =>
  ({ type: 'group', key, label, icon, items, ...opts })

export interface PanelDef {
  key: string
  to: string
  label: string
  icon: FunctionalComponent
  nav: NavEntry[]
}

// Each user sees ONLY their role's panel — no switcher.
// SUPERADMIN nav reflects the new domain (Branch / Programs / Geography / Diploms catalog).

const ADMIN_NAV: NavEntry[] = [
  leaf('/admin', 'Bosh sahifa', LayoutDashboard, 'violet'),

  group('crm', 'CRM — Leadlar', Inbox, [
    leaf('/admin/leads',                'Lead\'lar ro\'yxati',   Inbox,          'amber'),
    leaf('/admin/leads/board',          'Varonka',                LayoutGrid,     'indigo'),
    leaf('/admin/leads/new',            'Yangi lead',             FilePlus2,      'emerald'),
    leaf('/admin/lead-settings',        'Sozlamalar',             Settings,       'slate'),
  ]),

  group('admissions', 'Qabul jarayoni', ClipboardList, [
    leaf('/admin/applicants',           'Abituriyentlar',         UsersIcon,      'violet'),
    leaf('/admin/applications',         'Arizalar',               ClipboardList,  'amber'),
    leaf('/admin/diploms',              'Diplomlar (1-kurs)',     Award,          'emerald'),
    leaf('/admin/transfer-diploms',     'Perevod diplomlari',     Award,          'cyan'),
    leaf('/admin/payments',             "To'lovlar",              CreditCard,     'teal'),
  ]),

  group('programs', "Ta'lim", School, [
    leaf('/admin/branches',             'Filiallar',              Building2,      'rose'),
    leaf('/admin/programs',             "Yo'nalishlar",           GraduationCap,  'indigo'),
    leaf('/admin/education-levels',     "Ta'lim darajalari",      Layers,         'sky'),
    leaf('/admin/education-forms',      "Ta'lim shakllari",       BookOpen,       'pink'),
  ]),

  group('geo', 'Geografiya', MapPin, [
    leaf('/admin/countries',            'Davlatlar',              Globe,          'cyan'),
    leaf('/admin/regions',              'Viloyatlar',             MapPin,         'sky'),
    leaf('/admin/districts',            'Tumanlar',               MapPinned,      'indigo'),
  ]),

  group('catalog', 'Kataloglar', Library, [
    leaf('/admin/education-types',      "Ta'lim turlari",         GraduationCap,  'indigo'),
    leaf('/admin/institution-types',    'Muassasa turlari',       Building2,      'amber'),
    leaf('/admin/courses',              'Kurslar',                Layers,         'emerald'),
  ]),

  group('system', 'Sozlamalar', Settings, [
    leaf('/admin/users',                'Foydalanuvchilar',       UsersIcon,      'rose'),
    leaf('/admin/contract-templates',   'Shartnoma shabloni',     FilePlus2,      'violet'),
    leaf('/admin/contract-settings',    'Shartnoma sozlamalari',  Building2,      'indigo'),
    leaf('/admin/audit',                'Audit jurnali',          Shield,         'slate'),
  ]),

  // ROOT-ONLY group — filtered out at runtime for non-root users by panels store.
  group('root', 'Konsalting', Building2, [
    leaf('/admin/consulting-agencies',  'Konsalting agentliklari', Building2,     'indigo', { rootOnly: true }),
  ], { rootOnly: true }),
]

const OPERATOR_NAV: NavEntry[] = [
  leaf('/operator', 'Bosh sahifa', LayoutDashboard, 'violet'),
  group('crm', 'CRM', UsersIcon, [
    leaf('/operator/leads',          "Mening lead'larim", UsersIcon,     'violet'),
    leaf('/operator/leads/board',    'Varonka',            LayoutDashboard, 'sky'),
    leaf('/operator/stats',          'Mening statistikam', BarChart3,     'amber'),
  ]),
  group('admission', 'Qabul', ClipboardList, [
    leaf('/operator/applicants',     'Abituriyentlar',  UsersIcon,     'violet'),
    leaf('/operator/applications',   'Arizalar',        ClipboardList, 'amber'),
    leaf('/operator/contracts',      'Shartnomalar',    FileText,      'teal'),
    leaf('/operator/payments',       "To'lovlar",       CreditCard,    'emerald'),
  ]),
]

const DIRECTOR_NAV: NavEntry[] = [
  leaf('/director',              'Bosh sahifa',     LayoutDashboard, 'violet'),
  leaf('/director/applicants',   'Abituriyentlar',  UsersIcon,       'violet'),
  leaf('/director/applications', 'Arizalar',        ClipboardList,   'amber'),
]

const ACCOUNTANT_NAV: NavEntry[] = [
  leaf('/accountant',              'Bosh sahifa',     LayoutDashboard, 'violet'),
  leaf('/accountant/contracts',    'Shartnomalar',    FileText,        'teal'),
  leaf('/accountant/payments',     "To'lovlar",       CreditCard,      'emerald'),
  leaf('/accountant/applications', 'Arizalar',        ClipboardList,   'amber'),
  leaf('/accountant/applicants',   'Abituriyentlar',  UsersIcon,       'sky'),
]

const APPLICANT_NAV: NavEntry[] = [
  leaf('/applicant',              'Bosh sahifa',       LayoutDashboard, 'violet'),
  leaf('/applicant/profile',      "Ma'lumotlarim",     UsersIcon,       'indigo'),
  leaf('/applicant/programs',     "Yo'nalishlar",      GraduationCap,   'emerald'),
  leaf('/applicant/applications', 'Arizalarim',        ClipboardList,   'amber'),
  leaf('/applicant/contracts',    'Shartnomalarim',    FileText,        'teal'),
]

export const PANELS: Record<string, PanelDef> = {
  admin:      { key: 'admin',      to: '/admin',      label: 'Admin paneli',      icon: Settings as any,      nav: ADMIN_NAV },
  operator:   { key: 'operator',   to: '/operator',   label: 'Operator paneli',    icon: UsersIcon as any,    nav: OPERATOR_NAV },
  director:   { key: 'director',   to: '/director',   label: 'Direktor paneli',    icon: BarChart3 as any,    nav: DIRECTOR_NAV },
  accountant: { key: 'accountant', to: '/accountant', label: 'Buxgalter paneli',   icon: Wallet as any,       nav: ACCOUNTANT_NAV },
  applicant:  { key: 'applicant',  to: '/applicant',  label: 'Abituriyent paneli', icon: GraduationCap as any, nav: APPLICANT_NAV },
}

export const usePanelsStore = defineStore('panels', {
  getters: {
    /** Single panel for the current user's role. */
    currentPanel(): PanelDef | undefined {
      const role = useAuthStore().user?.role
      switch (role) {
        case 'superadmin':
        case 'admin':      return PANELS.admin
        case 'operator':   return PANELS.operator
        case 'director':   return PANELS.director
        case 'accountant': return PANELS.accountant
        case 'applicant':  return PANELS.applicant
        default:           return undefined
      }
    },
    nav(): NavEntry[] {
      const all = this.currentPanel?.nav || []
      const isRoot = useAuthStore().isRootSuperadmin
      // Filter root-only groups/leaves for non-root users.
      return all
        .filter(e => !(e.type === 'group' && e.rootOnly && !isRoot))
        .map(e => {
          if (e.type !== 'group') return e
          return { ...e, items: e.items.filter(l => !(l.rootOnly && !isRoot)) }
        })
        .filter(e => e.type !== 'group' || e.items.length > 0)
    },
  },
})

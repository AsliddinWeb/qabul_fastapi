import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import AuthLayout from '@/layouts/AuthLayout.vue'
import AppShell from '@/layouts/AppShell.vue'
import { redirectIfAuthenticated, requireAuth, requireRoles, rootRedirect } from '@/router/guards'

const ProfilePage = () => import('@/views/shared/ProfilePage.vue')

const routes: RouteRecordRaw[] = [
  // Smart root: authenticated → role home, otherwise → login.
  { path: '/', beforeEnter: rootRedirect, component: { render: () => null } },

  {
    path: '/auth',
    component: AuthLayout,
    beforeEnter: redirectIfAuthenticated,
    children: [
      { path: 'login',  name: 'phone-login', component: () => import('@/views/auth/PhoneLoginPage.vue'), meta: { title: 'Kirish' } },
      { path: 'verify', name: 'otp-verify',  component: () => import('@/views/auth/OtpVerifyPage.vue'),  meta: { title: "SMS-kodni tasdiqlash" } },
      { path: 'staff',  name: 'staff-login', component: () => import('@/views/auth/StaffLoginPage.vue'), meta: { title: "Xodim sifatida kirish" } },
    ],
  },

  // ----- Applicant -----
  {
    path: '/applicant',
    component: AppShell,
    beforeEnter: requireRoles(['applicant']),
    children: [
      { path: '',                  name: 'applicant-home',           component: () => import('@/views/applicant/DashboardPage.vue') },
      { path: 'profile',           name: 'applicant-profile',        component: () => import('@/views/applicant/ProfilePage.vue') },
      { path: 'programs',          name: 'applicant-programs',       component: () => import('@/views/applicant/ProgramsPage.vue') },
      { path: 'applications',      name: 'applicant-applications',   component: () => import('@/views/applicant/ApplicationsPage.vue'),     meta: { title: 'Mening arizalarim' } },
      { path: 'applications/:id',  name: 'applicant-application-id', component: () => import('@/views/applicant/ApplicationDetailPage.vue'),meta: { title: 'Ariza tafsiloti' } },
      { path: 'contracts',         name: 'applicant-contracts',      component: () => import('@/views/applicant/ContractsPage.vue'),        meta: { title: 'Shartnomalarim' } },
      { path: 'contracts/:id',     name: 'applicant-contract-id',    component: () => import('@/views/applicant/ContractDetailPage.vue'),   meta: { title: 'Shartnoma' } },
    ],
  },

  // ----- Operator -----
  {
    path: '/operator',
    component: AppShell,
    beforeEnter: requireRoles(['operator', 'admin', 'superadmin']),
    children: [
      { path: '',                  name: 'operator-home',          component: () => import('@/views/operator/DashboardPage.vue') },
      { path: 'profile',           name: 'operator-profile',       component: ProfilePage },

      // Applicants — share admin pages
      { path: 'applicants',        name: 'operator-applicants',    component: () => import('@/views/admin/ApplicantsPage.vue'),       meta: { title: 'Abituriyentlar' } },
      { path: 'applicants/new',    name: 'operator-applicant-new', component: () => import('@/views/operator/ApplicantNewPage.vue') },
      { path: 'applicants/:id',    name: 'operator-applicant',     component: () => import('@/views/operator/ApplicantDetailPage.vue') },

      // Applications — share admin pages
      { path: 'applications',      name: 'operator-applications',       component: () => import('@/views/admin/ApplicationsPage.vue'),      meta: { title: 'Arizalar' } },
      { path: 'applications/new',  name: 'operator-application-new',    component: () => import('@/views/admin/ApplicationFormPage.vue'),  meta: { title: 'Yangi ariza' } },
      { path: 'applications/:id',  name: 'operator-application-detail', component: () => import('@/views/admin/ApplicationDetailPage.vue'), meta: { title: 'Ariza' } },
      { path: 'applications/:id/edit', name: 'operator-application-edit', component: () => import('@/views/admin/ApplicationFormPage.vue'),  meta: { title: 'Arizani tahrirlash' } },

      // Contracts — share admin pages
      { path: 'contracts',         name: 'operator-contracts',     component: () => import('@/views/admin/ContractsPage.vue'),        meta: { title: 'Shartnomalar' } },
      { path: 'contracts/new',     name: 'operator-contract-new',  component: () => import('@/views/operator/ContractCreatePage.vue') },
      { path: 'contracts/:id',     name: 'operator-contract',      component: () => import('@/views/operator/ContractDetailPage.vue') },

      // Payments — share admin pages (read-mostly)
      { path: 'payments',          name: 'operator-payments',      component: () => import('@/views/admin/PaymentsPage.vue'),         meta: { title: "To'lovlar" } },

      // CRM (operator's own leads — reusing admin components, filtered by route path inside)
      { path: 'leads',          name: 'operator-leads',         component: () => import('@/views/admin/leads/LeadsListPage.vue'),  meta: { title: "Mening lead'larim", myOnly: true } },
      { path: 'leads/board',    name: 'operator-leads-board',   component: () => import('@/views/admin/leads/LeadsBoardPage.vue'), meta: { title: 'Kanban',              myOnly: true } },
      { path: 'leads/new',      name: 'operator-leads-new',     component: () => import('@/views/admin/leads/LeadNewPage.vue'),    meta: { title: 'Yangi lead' } },
      { path: 'leads/:id',      name: 'operator-leads-detail',  component: () => import('@/views/admin/leads/LeadDetailPage.vue'), meta: { title: 'Lead' } },
      { path: 'stats',          name: 'operator-stats',         component: () => import('@/views/operator/MyStatsPage.vue'),       meta: { title: 'Mening statistikam' } },
    ],
  },

  // ----- Admin / SuperAdmin -----
  {
    path: '/admin',
    component: AppShell,
    beforeEnter: requireRoles(['admin', 'superadmin']),
    children: [
      { path: '',                       name: 'admin-home',         component: () => import('@/views/admin/DashboardPage.vue'),         meta: { title: 'Bosh sahifa' } },
      { path: 'profile',                name: 'admin-profile',      component: ProfilePage,                                              meta: { title: 'Profil' } },

      { path: 'users',                  name: 'admin-users',        component: () => import('@/views/admin/UsersPage.vue'),              meta: { title: 'Foydalanuvchilar' } },
      { path: 'users/new',              name: 'admin-users-new',    component: () => import('@/views/admin/UserFormPage.vue'),           meta: { title: "Yangi foydalanuvchi" } },
      { path: 'users/:id/edit',         name: 'admin-users-edit',   component: () => import('@/views/admin/UserFormPage.vue'),           meta: { title: "Foydalanuvchini tahrirlash" } },

      // Programs domain (new shape: Branch + EduLevel + EduForm + Program)
      { path: 'branches',               name: 'admin-branches',     component: () => import('@/views/admin/BranchesPage.vue'),           meta: { title: 'Filiallar' } },
      { path: 'education-levels',       name: 'admin-edu-levels',   component: () => import('@/views/admin/EducationLevelsPage.vue'),    meta: { title: "Ta'lim darajalari" } },
      { path: 'education-forms',        name: 'admin-edu-forms',    component: () => import('@/views/admin/EducationFormsPage.vue'),     meta: { title: "Ta'lim shakllari" } },
      { path: 'programs',               name: 'admin-programs',     component: () => import('@/views/admin/ProgramsListPage.vue'),       meta: { title: "Yo'nalishlar" } },
      { path: 'programs/new',           name: 'admin-programs-new', component: () => import('@/views/admin/ProgramFormPage.vue'),        meta: { title: "Yangi yo'nalish" } },
      { path: 'programs/:id/edit',      name: 'admin-programs-edit',component: () => import('@/views/admin/ProgramFormPage.vue'),        meta: { title: "Yo'nalishni tahrirlash" } },

      // Geography (Country / Region / District)
      { path: 'countries',              name: 'admin-countries',    component: () => import('@/views/admin/CountriesPage.vue'),          meta: { title: 'Davlatlar' } },
      { path: 'regions',                name: 'admin-regions',      component: () => import('@/views/admin/RegionsPage.vue'),            meta: { title: 'Viloyatlar' } },
      { path: 'districts',              name: 'admin-districts',    component: () => import('@/views/admin/DistrictsPage.vue'),          meta: { title: 'Tumanlar' } },

      // Diploms catalog
      { path: 'education-types',        name: 'admin-edu-types',    component: () => import('@/views/admin/EducationTypesPage.vue'),     meta: { title: "Ta'lim turlari" } },
      { path: 'institution-types',      name: 'admin-inst-types',   component: () => import('@/views/admin/InstitutionTypesPage.vue'),   meta: { title: 'Muassasa turlari' } },
      { path: 'courses',                name: 'admin-courses',      component: () => import('@/views/admin/CoursesPage.vue'),            meta: { title: 'Kurslar' } },

      // Diploms (placeholder lists)
      { path: 'diploms',                name: 'admin-diploms',      component: () => import('@/views/admin/DiplomsPage.vue'),            meta: { title: 'Diplomlar' } },
      { path: 'transfer-diploms',       name: 'admin-transfer-diploms', component: () => import('@/views/admin/TransferDiplomsPage.vue'), meta: { title: 'Perevod diplomlari' } },

      // Applicants / applications / contracts / payments (admin-specific full CRUD)
      { path: 'applicants',             name: 'admin-applicants',   component: () => import('@/views/admin/ApplicantsPage.vue'),         meta: { title: 'Abituriyentlar' } },
      { path: 'applicants/new',         name: 'admin-applicants-new', component: () => import('@/views/operator/ApplicantNewPage.vue'),  meta: { title: "Yangi abituriyent" } },
      { path: 'applicants/:id',         name: 'admin-applicant-detail', component: () => import('@/views/operator/ApplicantDetailPage.vue'), meta: { title: 'Abituriyent' } },
      { path: 'applications',           name: 'admin-applications', component: () => import('@/views/admin/ApplicationsPage.vue'),       meta: { title: 'Arizalar' } },
      { path: 'applications/new',       name: 'admin-applications-new', component: () => import('@/views/admin/ApplicationFormPage.vue'),  meta: { title: 'Yangi ariza' } },
      { path: 'applications/:id',       name: 'admin-applications-detail', component: () => import('@/views/admin/ApplicationDetailPage.vue'), meta: { title: 'Ariza tafsiloti' } },
      { path: 'applications/:id/edit',  name: 'admin-applications-edit',component: () => import('@/views/admin/ApplicationFormPage.vue'),  meta: { title: 'Arizani tahrirlash' } },
      { path: 'contracts',              name: 'admin-contracts',    component: () => import('@/views/admin/ContractsPage.vue'),          meta: { title: 'Shartnomalar' } },
      { path: 'contracts/new',          name: 'admin-contract-new', component: () => import('@/views/operator/ContractCreatePage.vue'), meta: { title: 'Shartnoma yaratish' } },
      { path: 'contracts/:id',          name: 'admin-contract-detail', component: () => import('@/views/operator/ContractDetailPage.vue'), meta: { title: 'Shartnoma' } },
      { path: 'payments',               name: 'admin-payments',     component: () => import('@/views/admin/PaymentsPage.vue'),           meta: { title: "To'lovlar" } },

      // CRM — Leads
      { path: 'leads',                  name: 'admin-leads',        component: () => import('@/views/admin/leads/LeadsListPage.vue'),    meta: { title: 'Leadlar' } },
      { path: 'leads/board',            name: 'admin-leads-board',  component: () => import('@/views/admin/leads/LeadsBoardPage.vue'),   meta: { title: 'Leadlar — Kanban' } },
      { path: 'leads/new',              name: 'admin-leads-new',    component: () => import('@/views/admin/leads/LeadNewPage.vue'),      meta: { title: 'Yangi lead' } },
      { path: 'leads/:id',              name: 'admin-leads-detail', component: () => import('@/views/admin/leads/LeadDetailPage.vue'),   meta: { title: 'Lead tafsiloti' } },
      { path: 'lead-settings',          name: 'admin-lead-settings', component: () => import('@/views/admin/leads/LeadSettingsPage.vue'), meta: { title: 'Lead sozlamalari' } },

      { path: 'audit',                  name: 'admin-audit',        component: () => import('@/views/admin/AuditLogPage.vue'),           meta: { title: 'Audit jurnali' } },
      { path: 'audit/:id',              name: 'admin-audit-detail', component: () => import('@/views/admin/AuditDetailPage.vue'),        meta: { title: 'Audit yozuvi' } },

      { path: 'contract-templates',     name: 'admin-templates',    component: () => import('@/views/admin/ContractTemplatesPage.vue'),    meta: { title: 'Shartnoma shabloni' } },
      { path: 'contract-templates/new', name: 'admin-template-new', component: () => import('@/views/admin/ContractTemplateEditor.vue'),  meta: { title: 'Yangi shablon' } },
      { path: 'contract-templates/:id', name: 'admin-template-edit',component: () => import('@/views/admin/ContractTemplateEditor.vue'),  meta: { title: 'Shablonni tahrirlash' } },
      { path: 'contract-settings',      name: 'admin-contract-settings', component: () => import('@/views/admin/ContractSettingsPage.vue'),  meta: { title: 'Shartnoma sozlamalari' } },
    ],
  },

  // ----- Director -----
  {
    path: '/director',
    component: AppShell,
    beforeEnter: requireRoles(['director', 'admin', 'superadmin']),
    children: [
      { path: '',             name: 'director-home',         component: () => import('@/views/director/DashboardPage.vue') },
      { path: 'profile',      name: 'director-profile',      component: ProfilePage },
      { path: 'applicants',   name: 'director-applicants',   component: () => import('@/views/admin/ApplicantsPage.vue') },
      { path: 'applications', name: 'director-applications', component: () => import('@/views/admin/ApplicationsPage.vue') },
    ],
  },

  // ----- Accountant -----
  {
    path: '/accountant',
    component: AppShell,
    beforeEnter: requireRoles(['accountant', 'admin', 'superadmin']),
    children: [
      { path: '',                                name: 'accountant-home',     component: () => import('@/views/accountant/DashboardPage.vue') },
      { path: 'profile',                         name: 'accountant-profile',  component: ProfilePage },
      { path: 'contracts',                       name: 'accountant-contracts',component: () => import('@/views/accountant/ContractsListPage.vue') },
      { path: 'contracts/:contractId/payments',  name: 'accountant-payments-contract', component: () => import('@/views/accountant/PaymentsPage.vue') },
      { path: 'applications/:id/payments',       name: 'accountant-payments', component: () => import('@/views/accountant/PaymentsPage.vue') },
    ],
  },

  { path: '/forbidden',       name: 'forbidden',  component: () => import('@/views/public/ForbiddenPage.vue') },
  { path: '/:pathMatch(.*)*', name: 'not-found',  component: () => import('@/views/public/NotFoundPage.vue') },
]

const router = createRouter({
  history: createWebHistory('/app/'),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  const title = (to.meta?.title as string) || 'XIU Qabul'
  document.title = `${title} — XIU Qabul`
})

export { requireAuth }
export default router

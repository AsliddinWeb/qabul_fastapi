// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-04-01',
  devtools: { enabled: true },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/sitemap',
    '@nuxtjs/robots',
  ],

  css: ['~/assets/css/main.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'uz' },
      title: 'Xalqaro Innovatsion Universiteti — Onlayn Qabul',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: '#2d3dd1' },
        { name: 'application-name', content: 'XIU Qabul' },
        { name: 'apple-mobile-web-app-title', content: 'XIU Qabul' },
        {
          name: 'description',
          content:
            "Xalqaro Innovatsion Universiteti onlayn qabul tizimi. Telefon orqali ro'yxatdan o'ting va arizangizni topshiring.",
        },
        { name: 'keywords', content: "qabul, universitet, XIU, abituriyent, ariza, ta'lim" },
        { property: 'og:type', content: 'website' },
        { property: 'og:title', content: 'XIU — Onlayn Qabul' },
        { property: 'og:description', content: 'Xalqaro Innovatsion Universitetiga onlayn ariza topshirish.' },
        { property: 'og:image', content: '/og-image.png' },
        { property: 'og:locale', content: 'uz_UZ' },
      ],
      link: [
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' },
        { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16x16.png' },
        { rel: 'shortcut icon', href: '/favicon.ico' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
        },
      ],
    },
  },

  runtimeConfig: {
    public: {
      appUrl: process.env.NUXT_PUBLIC_APP_URL || '/app',
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || '/api/v1',
      siteUrl: process.env.NUXT_PUBLIC_SITE_URL || 'https://qabul.xiuedu.uz',
    },
  },

  site: {
    url: process.env.NUXT_PUBLIC_SITE_URL || 'https://qabul.xiuedu.uz',
    name: 'XIU Qabul',
  },

  nitro: {
    preset: 'node-server',
  },
})

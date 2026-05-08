<script setup lang="ts">
const year = new Date().getFullYear()
const config = useRuntimeConfig()
const appUrl = (config.public as any).appUrl || '/app'

function go(id: string) {
  if (typeof document === 'undefined') return
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  else if (id === 'home') window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <footer class="mt-auto"
          :style="{ background: 'rgb(var(--bg))', borderTop: '1px solid rgb(var(--border))' }">
    <div class="container-x py-14">
      <div class="grid lg:grid-cols-12 gap-10">
        <!-- Brand block -->
        <div class="lg:col-span-5">
          <div class="flex items-center gap-3 mb-4">
            <img src="/logo.webp" alt="XIU" class="w-10 h-10 rounded-xl shadow-sm object-contain" loading="lazy" />
            <div class="leading-[1.05]">
              <div class="text-[14px] font-bold tracking-tight" :style="{ color: 'rgb(var(--fg))' }">
                Xalqaro innovatsion
              </div>
              <div class="text-[14px] font-bold tracking-tight" :style="{ color: 'rgb(var(--fg-muted))' }">
                universiteti
              </div>
            </div>
          </div>
          <p class="text-sm leading-relaxed max-w-md" :style="{ color: 'rgb(var(--fg-soft))' }">
            Bakalavr va magistratura yo'nalishlari. Onlayn qabul tizimi orqali ariza topshiring.
          </p>

          <div class="mt-6 flex items-center gap-2">
            <a v-for="s in [
              { name: 'Telegram',  href: 'https://t.me/xalqaro_innovatsion_universiteti' },
              { name: 'Instagram', href: 'https://instagram.com/xiuedu' },
              { name: 'Facebook',  href: 'https://facebook.com/xiuedu' },
            ]" :key="s.name"
              :href="s.href" :title="s.name" target="_blank" rel="noopener"
              class="grid place-items-center w-9 h-9 rounded-full transition-all duration-200 hover:-translate-y-0.5"
              :style="{ background: 'rgb(var(--bg-soft))', color: 'rgb(var(--fg-soft))', border: '1px solid rgb(var(--border))' }"
            >
              <svg v-if="s.name === 'Telegram'" xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                <path d="M22.05 1.577c-.393-.016-.784.08-1.117.235-.484.186-21.79 8.413-22.62 8.711-.83.298-.83 1.27 0 1.568.32.115 4.286 1.659 5.95 2.301a1 1 0 0 0 .708-.005l9.66-3.836c.295-.117.566.158.404.42L9.05 18.92c-.123.158-.07.39.106.477l9.07 4.45c.38.186.838-.012.99-.42L23.86 2.96c.21-.563-.282-1.404-.81-1.382z"/>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path v-if="s.name === 'Instagram'" d="M12 2H8a4 4 0 0 0-4 4v12a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4V8a4 4 0 0 0-4-4M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37zM17.5 6.5h.01" />
                <path v-else d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
              </svg>
            </a>
          </div>
        </div>

        <!-- Quick links -->
        <div class="lg:col-span-3">
          <h4 class="text-[11px] font-bold mb-4 uppercase tracking-[0.10em]"
              :style="{ color: 'rgb(var(--fg-muted))' }">Sahifalar</h4>
          <ul class="space-y-2.5 text-sm">
            <li><a href="#programs" @click.prevent="go('programs')" class="transition-colors hover:text-[rgb(var(--brand))]" :style="{ color: 'rgb(var(--fg-soft))' }">Yo'nalishlar</a></li>
            <li><a href="#about" @click.prevent="go('about')" class="transition-colors hover:text-[rgb(var(--brand))]" :style="{ color: 'rgb(var(--fg-soft))' }">Universitet</a></li>
            <li><a href="#contact" @click.prevent="go('contact')" class="transition-colors hover:text-[rgb(var(--brand))]" :style="{ color: 'rgb(var(--fg-soft))' }">Bog'lanish</a></li>
            <li><a :href="`${appUrl}/auth/login`" class="transition-colors hover:text-[rgb(var(--brand))]" :style="{ color: 'rgb(var(--fg-soft))' }">Tizimga kirish</a></li>
          </ul>
        </div>

        <!-- Contact -->
        <div class="lg:col-span-4">
          <h4 class="text-[11px] font-bold mb-4 uppercase tracking-[0.10em]"
              :style="{ color: 'rgb(var(--fg-muted))' }">Aloqa</h4>
          <ul class="space-y-3 text-sm">
            <li class="flex items-start gap-2.5">
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="shrink-0 mt-0.5"
                   :style="{ color: 'rgb(var(--fg-muted))' }">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.37 1.9.72 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.35 1.85.59 2.81.72A2 2 0 0 1 22 16.92z" />
              </svg>
              <a href="tel:+998554061515" class="transition-colors hover:text-[rgb(var(--brand))]" :style="{ color: 'rgb(var(--fg-soft))' }">+998 55 406 15 15</a>
            </li>
            <li class="flex items-start gap-2.5">
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="shrink-0 mt-0.5"
                   :style="{ color: 'rgb(var(--fg-muted))' }">
                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z M22 6 12 13 2 6" />
              </svg>
              <a href="mailto:info@xiuedu.uz" class="transition-colors hover:text-[rgb(var(--brand))]" :style="{ color: 'rgb(var(--fg-soft))' }">info@xiuedu.uz</a>
            </li>
            <li class="flex items-start gap-2.5">
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="shrink-0 mt-0.5"
                   :style="{ color: 'rgb(var(--fg-muted))' }">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
              </svg>
              <span :style="{ color: 'rgb(var(--fg-soft))' }">Qarshi sh., I.Karimov ko‘chasi, 405-uy</span>
            </li>
          </ul>
        </div>
      </div>

      <div class="mt-12 pt-6 text-xs flex items-center justify-between"
           :style="{ borderTop: '1px solid rgb(var(--border))', color: 'rgb(var(--fg-muted))' }">
        <span>© {{ year }} Xalqaro Innovatsion Universiteti</span>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
const year = new Date().getFullYear()
const config = useRuntimeConfig()
const appUrl = (config.public as any).appUrl || '/app'
const loginUrl = `${appUrl}/auth/login`

const route = useRoute()
const router = useRouter()
function go(id: string) {
  if (route.path !== '/') { router.push({ path: '/', hash: `#${id}` }); return }
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <footer class="xrd foot">
    <div class="shell">
      <div class="foot__grid">
        <div>
          <a class="brand" href="#home" @click.prevent="go('home')">
            <img src="/logo.webp" alt="XIU logotipi" width="38" height="38" loading="lazy" />
            <span><b>Xalqaro innovatsion</b><small>Universiteti</small></span>
          </a>
          <p class="foot__about">Qarshi shahridagi nodavlat oliy ta'lim muassasasi. Bakalavr va magistratura yo'nalishlari.</p>
        </div>

        <div>
          <h4>Ta'lim</h4>
          <ul>
            <li><a href="#programs" @click.prevent="go('programs')">Yo'nalishlar</a></li>
            <li><a href="#qabul" @click.prevent="go('qabul')">Qabul tartibi</a></li>
            <li><a href="#hamkorlik" @click.prevent="go('hamkorlik')">Xalqaro hamkorlik</a></li>
          </ul>
        </div>

        <div>
          <h4>Universitet</h4>
          <ul>
            <li><a href="#about" @click.prevent="go('about')">Biz haqimizda</a></li>
            <li><a href="#contact" @click.prevent="go('contact')">Aloqa</a></li>
            <li><a :href="loginUrl">Tizimga kirish</a></li>
          </ul>
        </div>

        <div>
          <h4>Bog'lanish</h4>
          <ul>
            <li><a class="mono" href="tel:+998554061515">+998 55 406 15 15</a></li>
            <li><a href="mailto:info@xiuedu.uz">info@xiuedu.uz</a></li>
            <li><a href="https://t.me/xalqaro_innovatsion_universiteti" target="_blank" rel="noopener noreferrer">Telegram</a></li>
          </ul>
        </div>
      </div>

      <div class="foot__bar">
        <p>&copy; {{ year }} Xalqaro Innovatsion Universiteti. Barcha huquqlar himoyalangan.</p>
        <div class="foot__social">
          <a class="tg" href="https://t.me/xalqaro_innovatsion_universiteti" target="_blank" rel="noopener noreferrer" aria-label="Telegram"><i class="ph ph-telegram-logo" aria-hidden="true"></i></a>
          <a class="ig" href="https://www.instagram.com/xiu_edu.uz/" target="_blank" rel="noopener noreferrer" aria-label="Instagram"><i class="ph ph-instagram-logo" aria-hidden="true"></i></a>
          <a class="fb" href="https://www.facebook.com/p/Xalqaro-Innovatsion-Universiteti-100090241119598/" target="_blank" rel="noopener noreferrer" aria-label="Facebook"><i class="ph ph-facebook-logo" aria-hidden="true"></i></a>
        </div>
      </div>
    </div>
  </footer>
</template>

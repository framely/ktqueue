import Vue from 'vue'
import Vuex from 'vuex'
import VueRouter from 'vue-router'
import VueResource from 'vue-resource'
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-default/index.css'

import App from './App.vue'
import Jobs from './Jobs.vue'
import JobLog from './JobLog.vue'
import Repos from './Repos.vue'
import Login from './Login.vue'

Vue.use(ElementUI)
Vue.use(VueRouter)
Vue.use(VueResource)
Vue.use(Vuex)

const routes = [
  { path: '/', name: 'jobs', redirect: '/jobs', meta: { requireAuth: true }},
  { path: '/jobs', component: Jobs, meta: { requireAuth: true }},
  { path: '/jobs/:jobName/log', component: JobLog, meta: { requireAuth: true }},
  { path: '/repos', name: 'repos', component: Repos, meta: { requireAuth: true }},
  { path: '/login', name: 'login', component: Login, meta: { requireAuth: false }}
]

const router = new VueRouter({ routes })

const store = new Vuex.Store({
  strict: process.env.NODE_ENV !== 'production',
  state: {
    userInfo: {
      username: window.localStorage['username']
    }
  },
  mutations: {
    updateUserInfo (state, newUserInfo) {
      state.userInfo = newUserInfo
    }
  }
})

// auth
router.beforeEach((to, from, next) => {
  if (to.meta.requireAuth && store.state.userInfo.username == null) {
    next({ path: '/login' })
  } else {
    next()
  }
})

new Vue({
  router,
  store,
  el: '#app',
  render: h => h(App),
  created () {
    this.$http.get('/api/current_user').then((response) => {
      this.$store.commit('updateUserInfo', { username: response.body.user })
      window.localStorage['username'] = response.body.user
      if (this.$route.path === '/login') {
        this.$router.push('/')
      }
    }).catch((response) => {
      this.$store.commit('updateUserInfo', { username: null })
      delete window.localStorage['username']
    })
  }
})

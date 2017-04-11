import Vue from 'vue'
import VueRouter from 'vue-router'
import VueResource from 'vue-resource'
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-default/index.css'

import App from './App.vue'
import Jobs from './Jobs.vue'
import JobLog from './JobLog.vue'
import Repos from './Repos.vue'

Vue.use(ElementUI)
Vue.use(VueRouter)
Vue.use(VueResource)

new Vue({
  el: '#app',
  render: h => h(App),
  router: new VueRouter({
    routes: [
      { path: '/', name: 'jobs', redirect: '/jobs' },
      { path: '/jobs', component: Jobs },
      { path: '/jobs/:job_name/log', component: JobLog },
      { path: '/repos', name: 'repos', component: Repos }
    ]
  })
})

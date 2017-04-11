<template>
<div id="app">
  <div id="tq-header">
  </div>
  <el-menu :default-active="$route.path" mode="horizontal" :router="true">
    <h2 id="tq-title">KTQueue</h2>
    <el-menu-item index="/jobs" :route="{path: '/jobs'}">Jobs</el-menu-item>
    <el-menu-item index="/repos" :route="{path: '/repos'}">Repos</el-menu-item>
    <el-menu-item v-if="currentUser" index="currentUser" :route="{}">{{currentUser}}</el-menu-item>
    <el-menu-item v-else index="login" :route="{}"><a href="/oauth2/start">Login</a></el-menu-item>
  </el-menu>
  <router-view :check-auth="checkAuth" :current-user="currentUser"></router-view>
</div>
</template>

<script>

export default {
  name: 'app',
  data () {
    return {
      currentUser: null,
      authRequired: false
    }
  },
  mounted: function () {
    this.loadCurrentUser()
  },
  methods: {
    loadCurrentUser: function () {
      this.$http.get('/api/current_user').then(function (resource) {
        this.currentUser = resource.body.user
        this.authRequired = resource.body.authRequired
      })
    },
    checkAuth: function () {
      if (this.currentUser === null && this.auth_required) {
        window.location = 'oauth2/start'
        return false
      }
      return true
    }
  }
}
</script>

<style lang="scss">
#tq-header {
}
#tq-title {
  vertical-align: middle;
  line-height: 60px;
  float: left;
  margin: 0 2em 0 1em;
}
</style>

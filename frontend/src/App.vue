<template>
<div id="app">
  <div id="tq-header">
  </div>
  <el-menu :default-active="$route.path" mode="horizontal" :router="true">
    <h2 id="tq-title">KTQueue</h2>
    <el-menu-item index="/jobs" :route="{path: '/jobs'}">Jobs</el-menu-item>
    <el-menu-item index="/repos" :route="{path: '/repos'}">Repos</el-menu-item>
    <el-submenu v-if="$store.state.userInfo.username" index="currentUser">
      <template slot="title">{{$store.state.userInfo.username}}</template>
      <el-menu-item index="logout" :route="{}" @click="logout">Logout</el-menu-item>
    </el-submenu>
    <el-menu-item v-else index="login" :route="{}"><a href="/auth/oauth2/start">Login</a></el-menu-item>
  </el-menu>
  <router-view></router-view>
</div>
</template>

<script>
export default {
  name: 'app',
  data () {
    return {
    }
  },
  mounted () {
  },
  methods: {
    logout () {
      this.$http.delete('./api/current_user', this.form).then((response) => {
        this.$store.commit('updateUserInfo', { username: null })
        delete window.localStorage['username']
        this.$message.success('Successful logout')
        this.$router.replace('/login')
      }).catch((response) => {
        this.$message.errr('Can not logout')
        console.error(response.body)
      })
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

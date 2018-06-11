<template>
  <div class="login-form">
    <p>  <a href="./auth/oauth2/start"><el-button type="primary">Login</el-button></a> </p>
  </div>
</template>
<style>
  .login-form {
    margin: 10px auto;
    padding: 10px 80px;
    text-align: center;
    width: 200px;
    border: 1px solid #ccc;
    border-radius: 10px;
    background-color: #eee

  }
</style>
<script>
export default {
  name: 'app',
  data () {
    return {
    }
  },
  mounted () {
    if (this.$store.state.userInfo.username) {
      this.$router.replace('/')
    }
  }
}
</script>

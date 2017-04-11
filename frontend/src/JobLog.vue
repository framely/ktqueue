<template>
  <div>
    <el-select v-model="selectedVersion" placeholder="" @change="versionChange">
      <el-option
        v-for="version in versions"
        :label="version"
        :value="version"
        :key="version">
      </el-option>
    </el-select>
    <el-switch
      v-model="lineWrap"
      :width="90"
      on-text="Wrap"
      off-text="No wrap">
    </el-switch>
    <a :download="this.$route.params.jobName + '.' + this.$route.query.version + '.txt'" :href="'jobs/' + this.$route.params.jobName + '/log/' + this.$route.query.version">
      <el-button type='text'>Download</el-button>
    </a>
    <pre class="ktq-log-text" v-bind:class="{'ktq-log-wrap': lineWrap}">{{log_text}}</pre>
  </div>
</template>
<script>
export default {
  template: '#tq-job-log-template',
  data: function () {
    return {
      logText: '',
      selectedVersion: null,
      versions: [],
      lineWrap: false
    }
  },
  mounted: function () {
    this.loadJobLogVersions(this.$route.params.jobName)
  },
  methods: {
    loadJobLog: function (jobName, version) {
      if (version === null) {
        return
      }
      var loading = this.$loading({
        target: '.ktq-log-text',
        text: 'loading log'
      })
      this.$http.get('/jobs/' + jobName + '/log/' + version).then(function (resource) {
        this.logText = resource.body
        loading.close()
      }).catch(function (response) {
        this.$message.error('Unable to load Log!\n')
        console.error(response.body)
        loading.close()
      })
    },
    loadJobLogVersions: function (jobName) {
      this.$http.get('/jobs/' + jobName + '/log/version').then(function (resource) {
        this.versions = resource.body.versions
        if (this.versions.length === 0) {
          this.selectedVersion = null
          return
        }
        if (this.$route.query.version) {
          this.selectedVersion = this.$route.query.version
          return
        }
        if (this.versions.indexOf('current') !== -1) {
          this.selectedVersion = 'current'
        } else {
          this.selectedVersion = this.versions[this.versions.length - 1]
        }
      }).catch(function (response) {
        this.$message.error('Unable to load Log versions!\n')
        console.error(response.body)
      })
    },
    versionChange: function (version) {
      this.$router.replace({ query: { version: version }})
      this.loadJobLog(this.$route.params.jobName, version)
    }
  }
}
</script>
<style lang="scss">
.ktq-log-wrap {
  white-space: pre-wrap;
}
</style>

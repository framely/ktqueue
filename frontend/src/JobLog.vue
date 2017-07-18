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
    <el-switch
      v-if="selectedVersion == 'current'"
      class="follow-switch"
      v-model="follow"
      on-text="Follow"
      off-text="Static"
      :width="100"
      @change="followChange"
    >
    </el-switch>
    <a :download="this.$route.params.jobName + '.' + this.$route.query.version + '.txt'" :href="'api/jobs/' + this.$route.params.jobName + '/log/' + this.$route.query.version">
      <el-button type='text'>Download</el-button>
    </a>
    <pre class="ktq-log-text" v-bind:class="{'ktq-log-wrap': lineWrap}">{{logText}}<span class="new-log-text">{{newLogText}}</span></pre>
  </div>
</template>
<script>
export default {
  template: '#tq-job-log-template',
  data: function () {
    return {
      logText: '',
      newLogText: '',
      selectedVersion: null,
      versions: [],
      lineWrap: false,
      wscon: null,
      follow: false
    }
  },
  mounted: function () {
    this.loadJobLogVersions(this.$route.params.jobName)
  },
  beforeDestroy () {
    this.stopWebSocketFollow()
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
      this.$http.get('/api/jobs/' + jobName + '/log/' + version).then(function (resource) {
        this.logText = resource.body
        this.newLogText = ''
        loading.close()
      }).catch(function (response) {
        this.$message.error('Unable to load Log!\n')
        console.error(response.body)
        loading.close()
      })
    },
    loadJobLogVersions: function (jobName) {
      this.$http.get('/api/jobs/' + jobName + '/log/version').then(function (resource) {
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
      if (version === 'current') {
        this.follow = true
        this.startWebSocketFollow(this.$route.params.jobName)
      } else {
        this.stopWebSocketFollow()
        this.loadJobLog(this.$route.params.jobName, version)
      }
    },
    followChange: function (follow) {
      if (follow) {
        this.startWebSocketFollow(this.$route.params.jobName)
      } else {
        this.stopWebSocketFollow()
        this.loadJobLog(this.$route.params.jobName, this.selectedVersion)
      }
    },
    startWebSocketFollow: function (jobName) {
      this.stopWebSocketFollow()
      // eslint-disable-next-line
      let schema = window.location.protocol.startsWith('https') ? 'wss://' : 'ws://'
      var con = new WebSocket(schema + window.location.host + '/wsapi/jobs/' + jobName + '/log' + '?tailLines=1000')
      con.onmessage = event => {
        this.logText += this.newLogText
        const pos = this.logText.length -  50 * 1024
        if (pos > 0) {
          this.logText = this.logText.slice(pos + 1)
        }
        this.newLogText = event.data
      }
      var onerror = error => {
        this.$notify({
          title: 'Log follow is stopped',
          message: 'Please refresh this page.',
          duration: 0,
          type: 'error'
        })
        console.error(error)
        this.wscon = null
      }
      con.onerror = onerror
      con.onclose = (event) => {
        if (event.code > 1000) {
          onerror(event)
        }
      }
      this.wscon = con
      this.logText = ''
      this.newLogText = ''
      this.wsclosing = false
    },
    stopWebSocketFollow () {
      if (this.wscon) {
        this.wscon.close(1000)
        this.wscon = null
      }
    }
  }
}
</script>
<style lang="scss">
.ktq-log-wrap {
  white-space: pre-wrap;
}
.new-log-text {
  background-color: #D3DCE6;
}
.follow-switch {
  position: fixed;
  top: 100px;
  right: 60px;
}
</style>

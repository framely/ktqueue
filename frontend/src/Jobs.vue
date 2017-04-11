<template>
  <div>
    <div class="table-header">
      <el-button size="small" type="primary" @click="showCreateJob">Create Job</el-button>
      <el-radio-group v-model="jobsFilter" size="small" @change="jobsFilterChange">
        <el-radio-button label="All"></el-radio-button>
        <el-radio-button label="Hidden"></el-radio-button>
        <el-radio-button label="Fav"></el-radio-button>
        <el-radio-button label="Running"></el-radio-button>
      </el-radio-group>
      <el-pagination
        layout="prev, pager, next, sizes"
        :page-size="jobsData.pageSize"
        :total="jobsData.total"
        :current-page="jobsData.page"
        @current-change="pageCurrentChange"
        @size-change="pageSizeChange"
        >
      </el-pagination>
    </div>
    <el-table
      :data="jobsData.data"
      style="width: 100%"
      :row-class-name="tableRowClassName"
      @filter-change="jobsFilterChange"
      v-loading="jobsData.loading">
      <el-table-column type="expand">
       <template scope="scope">
         <div class="job-expand-item"><label>name: </label><div>{{ scope.row.name }}</div></div>
         <div class="job-expand-item"><label>repo: </label><div>{{ scope.row.repo }}</div></div>
         <div class="job-expand-item"><label>branch: </label><div>{{ scope.row.branch }}</div></div>
         <div class="job-expand-item"><label>commit_id: </label><div>{{ scope.row.commit_id }}</div></div>
         <div class="job-expand-item"><label>command: </label><div>{{ scope.row.command }}</div></div>
         <div class="job-expand-item"><label>comments: </label><div><pre>{{ scope.row.comments }}</pre></div></div>
         <div class="job-expand-item"><label>Edit: </label><el-button @click="editJob(scope.$index, jobsData.data)" type="text" size="small">Edit</el-button></div>
         <div class="job-expand-item"><label>Clone: </label><el-button @click="copyJob(scope.$index, jobsData.data)" type="text" size="small">Clone</el-button></div>
         <div class="job-expand-item">
           <label>Control: </label>
           <el-button v-if="scope.row.status.indexOf('Completed') != -1 || scope.row.status == 'ManualStop' || scope.row.status == 'FetchError'"  @click="restartJob(scope.$index, jobsData.data)" type="text" size="small">Restart</el-button>
           <el-button v-else @click="stopJob(scope.$index, jobsData.data)" type="text" size="small">Stop</el-button>
         </div>
         <div class="job-expand-item"><label>TensorBoard: </label>
           <el-button v-if="scope.row.tensorboard" @click="stopBoard(scope.$index, jobsData.data)" type="text" size="small">Stop</el-button>
           <el-button v-else @click="startBoard(scope.$index, jobsData.data)" type="text" size="small">Start</el-button>
         </div>
         <div class="job-expand-item"><label>Hide: </label>
           <div>
             <el-switch
               v-model="scope.row.hide"
               :width="70"
               on-text="Hide"
               off-text="Show"
               :disabled="scope.row.status == 'Running'"
               @change="jobHideChange(scope.row, $event)">
              </el-switch>
           </div>
         </div>
         <p v-if="scope.row.tensorboard">
           <a :href="'/tensorboard/' + scope.row.name + '/'">TensorBoard</a>
         </p>
       </template>
      </el-table-column>
      <el-table-column
        width="50">
        <template scope="scope">
          <el-button type="text" @click="toggleFavorite(scope.row, $event)">
            <i v-if="scope.row.fav" class="el-icon-star-on"/>
            <i v-else class="el-icon-star-off"/>
          </el-button>
        </template>
      </el-table-column>
      <el-table-column
        prop="name"
        label="name"
        :show-overflow-tooltip="true">
      </el-table-column>
      <el-table-column
        label="Node"
        width="100">
        <template scope="scope">
          {{ scope.row.runningNode || '' }}
        </template>
      </el-table-column>
      <el-table-column
        label="status"
        prop="status"
        width="120"

        header-align="left"
        :show-overflow-tooltip="true">
      </el-table-column>
      <el-table-column
        prop="gpu_num"
        label="GPUs"
        width="80"
        align="center">
      </el-table-column>
      <el-table-column
        label="creation"
        width="200">
        <template scope="scope">
          <span :title="moment(scope.row.creationTimestamp).fromNow()">{{scope.row.creationTimestamp ? moment(scope.row.creationTimestamp).format('YYYY-MM-DD HH:mm:SS'): ''}}</span>
        </template>
      </el-table-column>
      <el-table-column
        prop="user"
        label="user"
        width="110"
        :show-overflow-tooltip="true"
        :filters="filterUsers"
        columnKey="user"
        align="left">
      </el-table-column>
      <el-table-column
        label="Log"
        width="100">
        <template scope="scope">
          <router-link :to="{path: '/jobs/' + scope.row.name + '/log'}"><el-button type="text" size="small">Log</el-button></router-link>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog :title="createJobDialog.title" v-model="createJobDialog.visible" size="large">
      <el-form ref="form" :model="createJobDialog.data" label-width="95px">
        <el-form-item label="Name" required>
         <el-input v-model="createJobDialog.data.name"></el-input>
        </el-form-item>
        <el-form-item label="Node">
          <el-select v-model="createJobDialog.data.node" clearable placeholder="Any">
            <el-option
              v-for="item in nodes"
              :label="item.labels['kubernetes.io/hostname'] + ' (' + (item.gpu_capacity - item.gpu_used) + '/' + item.gpu_capacity + ')'"
              :value="item.labels['kubernetes.io/hostname']"
              :key="item.labels['kubernetes.io/hostname']">
            </el-option>
          </el-select>
          <label> (avail/total) </label>
        </el-form-item>
        <el-form-item label="GPUs">
         <el-input-number v-model="createJobDialog.data.gpu_num"></el-input-number>
        </el-form-item>
        <el-form-item label="Command" required>
         <el-input type="textarea" :rows=3 v-model="createJobDialog.data.command"></el-input>
        </el-form-item>
        <el-form-item label="Image" required>
         <el-input v-model="createJobDialog.data.image"></el-input>
        </el-form-item>
        <el-form-item label="Repo">
          <el-autocomplete v-model="createJobDialog.data.repo"
          :fetch-suggestions="repoQuerySearch"
          style="width: 100%"></el-autocomplete>
        </el-form-item>
        <el-form-item label="Branch">
         <el-input v-model="createJobDialog.data.branch"></el-input>
        </el-form-item>
        <el-form-item label="Commit id">
         <el-input v-model="createJobDialog.data.commit_id"></el-input>
        </el-form-item>
        <el-form-item label="Comments">
         <el-input type="textarea" :rows=3 v-model="createJobDialog.data.comments"></el-input>
        </el-form-item>
        <el-form-item v-for="(volume, index) in createJobDialog.data.volumeMounts"  :key="volume.key" :label="'Volume'" :rules="{
            required: true, message: 'volumeMounts should not be empty', trigger: 'blur'
          }">
          <el-col :span="10">
            <el-form-item>
              <el-input placeholder="hostPath" v-model="volume.hostPath" style="width: 100%;"></el-input>
            </el-form-item>
          </el-col>
          <span class="inline-form-span"> </span>
          <el-col :span="10">
           <el-form-item>
             <el-input placeholder="mountPath" v-model="volume.mountPath" style="width: 100%;"></el-input>
           </el-form-item>
          </el-col>
          <span class="inline-form-span"> </span>
          <el-button @click.prevent="removeVolume(volume)">删除</el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="addVolumeMount">Add volume</el-button>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="createJobDialog.visible = false">取 消</el-button>
        <el-button type="primary" @click="createJob">确 定</el-button>
      </span>
    </el-dialog>
  </div>
</template>
<script>
import * as moment from 'moment'
export default {
  template: '#tq-jobs-template',
  props: {
    checkAuth: Function,
    currentUser: String
  },
  data: function () {
    var defaultFilter = {
      jobsFilter: 'All',
      page: 1,
      pageSize: 20,
      user: null
    }
    return {
      defaultFilter: defaultFilter,
      jobsFilter: this.$route.query.jobsFilter || defaultFilter.jobsFilter,
      jobsFilterUser: this.$route.query.user || defaultFilter.jobsFilterUser,
      // pageSizeToGo: dealing with element-ui issue,
      // when you choose a large `pageSize`, which makes your current `page`,
      // element-ui will call not only `size-change` but also `current-change`
      // we use pageSizeToGo to eliminate incorrect `current-change` call
      pageSizeToGo: parseInt(this.$route.query.pageSize || defaultFilter.pageSize),
      jobsData: {
        count: 0,
        pageSize: parseInt(this.$route.query.pageSize || defaultFilter.pageSize),
        page: parseInt(this.$route.query.page || defaultFilter.page),
        loading: false,
        data: []
      },
      createJobDialog: {
        visible: false,
        title: 'Create Job',
        data: {
          name: '',
          node: null,
          // eslint-disable-next-line
          gpu_num: 1, // TODO
          command: '',
          image: '',
          repo: '',
          branch: '',
          // eslint-disable-next-line
          commit_id: '', // TODO
          comments: '',
          volumeMounts: []
        }
      },
      repos: [],
      nodes: []
    }
  },
  mounted: function () {
    this.loadJobs(this.jobsData.page, this.jobsData.pageSize)
    this.$http.get('/api/repos?pageSize=0&repo_only=1').then(function (resource) {
      for (var i = 0; i < resource.body.data.length; i++) {
        this.repos.push({ 'value': resource.body.data[i].repo })
      }
    })
    this.$http.get('/api/nodes').then(function (resource) {
      this.nodes = resource.body.items
    })
  },
  methods: {
    moment: moment,
    showCreateJob: function () {
      this.checkAuth()
      this.createJobDialog.title = 'Create Job'
      this.createJobDialog.visible = true
    },
    copyJob: function (index, tableData) {
      this.checkAuth()
      var line = tableData[index]
      Object.assign(this.createJobDialog.data, line)
      this.createJobDialog.visible = true
    },
    editJob: function (index, tableData) {
      this.checkAuth()
      var line = tableData[index]
      Object.assign(this.createJobDialog.data, line)
    },
    stopJob: function (index, tableData) {
      this.checkAuth()
      var jobName = tableData[index].name
      var $this = this
      this.$confirm('Do you really want to stop ' + jobName + '?', 'Stop job', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(function () {
        $this.$http.post('/api/job/stop/' + jobName, {}).then(function (resource) {
          $this.$message({
            type: 'success',
            message: jobName + ' stopped!'
          })
          $this.loadJobs(this.jobsData.page)
          $this.createJobDialog.visible = false
        })
      }).catch(function () {
        $this.$message({
          type: 'info',
          message: 'Cancel.'
        })
      })
    },
    restartJob: function (index, tableData) {
      this.checkAuth()
      var jobName = tableData[index].name
      var $this = this
      this.$confirm('Do you really want to Restart ' + jobName + '?', 'Restart job', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(function () {
        $this.$http.post('/api/job/restart/' + jobName, {}).then(function (resource) {
          $this.$message({
            type: 'success',
            message: jobName + ' Restarted!'
          })
          $this.loadJobs(this.jobsData.page)
          $this.createJobDialog.visible = false
        })
      }).catch(function () {
        $this.$message({
          type: 'info',
          message: 'Cancel.'
        })
      })
    },
    startBoard: function (index, tableData) {
      this.checkAuth()
      var line = tableData[index]
      var $this = this
      this.$prompt('Please enter logdir. You can use $JOB_NAME, $WORK_DIR, $OUTPUT_DIR', 'TensorBoard', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel'
      }).then(function (data) {
        $this.$http.post('/api/job/tensorboard/' + line.name, { 'logdir': data.value }).then(function () {
          $this.loadJobs($this.jobsData.page)
        })
      }).catch(function () {

      })
    },
    stopBoard: function (index, tableData) {
      this.checkAuth()
      var line = tableData[index]
      var $this = this
      this.$http.delete('/job/tensorboard/' + line.name).then(function () {
        $this.loadJobs($this.jobsData.page)
        this.$message({
          type: 'info',
          message: 'TensorBoard stopped.'
        })
      })
    },
    pageCurrentChange: function (page) {
      if (this.jobsData.pageSize !== this.pageSizeToGo) {
        return // deal with element-ui issue
      }
      this.loadJobs(page, this.jobsData.pageSize)
    },
    pageSizeChange: function (pageSize) {
      this.pageSizeToGo = pageSize
      this.loadJobs(Math.floor((this.jobsData.page - 1) * this.jobsData.pageSize / pageSize) + 1, pageSize)
    },
    loadJobs: function (page, pageSize) {
      pageSize = pageSize || this.jobsData.pageSize

      this.jobsData.loading = true
      var params = {}
      params['page'] = page
      if (this.jobsFilter === 'Hidden') {
        params['hide'] = '1'
      } else if (this.jobsFilter === 'Fav') {
        params['fav'] = '1'
      } else if (this.jobsFilter === 'Running') {
        params['status'] = 'Running'
        params['hide'] = 'all'
      }
      if (this.jobsFilterUser) {
        params['user'] = this.jobsFilterUser
      }
      params['pageSize'] = pageSize
      var routerQuery = {
        jobsFilter: this.jobsFilter,
        user: this.jobsFilterUser,
        page: page,
        pageSize: pageSize
      }
      for (var k in routerQuery) {
        if (routerQuery[k] === this.defaultFilter[k]) {
          delete routerQuery[k]
        }
      }
      this.$router.push({ query: routerQuery })
      this.$http.get('/api/jobs', { params: params }).then(function (resource) {
        resource.body.loading = false
        this.jobsData = resource.body
      })
    },
    createJob: function () {
      this.$http.post('/api/jobs', this.createJobDialog.data).then(function (resource) {
        this.loadJobs(1)
        this.createJobDialog.visible = false
      }).catch(function (response) {
        this.$message.error(response.body)
        console.error(response.body)
      })
    },
    repoQuerySearch: function (queryString, cb) {
      var repos = this.repos
      var results = queryString ? repos.filter(this.createFilter(queryString)) : repos
      console.log(results)
      cb(results)
    },
    createFilter: function (queryString) {
      return function (candidate) {
        return (candidate.value.indexOf(queryString.toLowerCase()) !== -1)
      }
    },
    addVolumeMount: function () {
      this.createJobDialog.data.volumeMounts.push({
        hostPath: '',
        mountPath: '',
        key: Date.now()
      })
    },
    removeVolume: function (volume) {
      var index = this.createJobDialog.data.volumeMounts.indexOf(volume)
      if (index !== -1) {
        this.createJobDialog.data.volumeMounts.splice(index, 1)
      }
    },
    jobHideChange: function (line, event) {
      this.$http.put('/api/jobs', {
        '_id': line._id,
        'hide': event
      }).then(function () {
        line.hide = event
      }).catch(function () {
        line.hide = !event
      })
      return !event
    },
    toggleFavorite: function (line, event) {
      var icon = event.target
      if (icon.tagName !== 'I') {
        icon = icon.querySelector('i')
      }
      icon.className = 'el-icon-loading'
      this.$http.put('/api/jobs', {
        '_id': line._id,
        'fav': !line.fav
      }).then(function () {
        line.fav = !line.fav
      }).catch(function () {
      })
    },
    jobsFilterChange: function (filter) {
      if (filter.constructor.name === 'Array') { // which mean table.filter-change call this function
        if (filter.user.length) {
          this.jobsFilterUser = filter.user[0]
        } else {
          this.jobsFilterUser = null
        }
      }
      this.loadJobs(this.jobsData.page)
    },
    tableRowClassName (row, index) {
      if (row.status === 'Running') {
        return 'positive-row'
      }
      return ''
    }
  },
  computed: {
    filterUsers: function () {
      var users = []
      if (this.currentUser) {
        users.push({ text: this.currentUser, value: this.currentUser })
      }
      return users
    }
  }
}
</script>
<style lang="scss">
.table-header {
  padding: .5em 0;
}
.table-header .el-pagination {
  display: inline-block;
}
.table-header .el-pagination,
.table-header .el-button,
.table-header .el-radio-group {
  vertical-align: middle;;
}
.inline-form-span {
  width: 1em;
  height: 1em;
  float: left;
}
.job-expand-item {
  margin-bottom: 10px;
  overflow: auto;
  zoom: 1;
}
.job-expand-item > label {
  width: 100px;
  float: left;
  text-align: right;
  padding-right: 1em;
  box-sizing: border-box;
}
.job-expand-item .el-tag+.el-tag {
  margin-left: 1em;
}
.job-expand-item > div {
  margin-left: 100px;
}
.job-expand-item  .el-button {
  padding: 0;
}
.job-expand-item > div > pre{
  margin: 0;
}
.status-stop-wrap {
  display: inline-block;
  width: 32px;
}
.el-table .positive-row {
  background: #e2f0e4;
}
</style>

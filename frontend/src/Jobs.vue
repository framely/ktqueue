<template>
  <div ref="rootdiv">
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
      @filter-change="jobsFilterChange">
      <el-table-column type="expand">
       <template scope="scope">
         <div class="job-expand-item"><label>name: </label><div>{{ scope.row.name }}</div></div>
         <div class="job-expand-item"><label>repo: </label><div>{{ scope.row.repo }}</div></div>
         <div class="job-expand-item"><label>branch: </label><div>{{ scope.row.branch }}</div></div>
         <div class="job-expand-item"><label>commit_id: </label><div>{{ scope.row.commit_id }}</div></div>
         <div class="job-expand-item"><label>command: </label><div>{{ scope.row.command }}</div></div>
         <div class="job-expand-item"><label>comments: </label><div><pre>{{ scope.row.comments }}</pre></div></div>
         <div class="job-expand-item"><label>Edit: </label><el-button @click="showEditJob(scope.$index, jobsData.data)" type="text" size="small">Edit</el-button></div>
         <div class="job-expand-item"><label>Clone: </label><el-button @click="showCloneJob(scope.$index, jobsData.data)" type="text" size="small">Clone</el-button></div>
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
               :disabled="scope.row.status != 'Completed' && scope.row.status != 'ManualStop' && scope.row.status != 'FetchError'"
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
        width="100"
        prop="runningNode"
        :filters="filterNodes"
        columnKey="node"
        :show-overflow-tooltip="true">
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
    <job-edit-dialog
      :title="editJobDialog.title"
      :nodes="nodes" :repos="repos"
      :show="editJobDialog.visible"
      :data="editJobDialog.data"
      :disabled-fields="editJobDialog.disabledFields"
      @confirm="onConfirmEdit"
      @cancel="() => editJobDialog.visible=false"
    />
  </div>
</template>
<script>
import moment from 'moment'
import { Loading } from 'element-ui'
import JobEditDialog from './JobEditDialog.vue'
import { defaultJobData } from './const.js'
export default {
  components: {
    JobEditDialog
  },
  props: {
    checkAuth: Function,
    currentUser: String
  },
  data: function () {
    var defaultFilter = {
      jobsFilter: 'All',
      page: 1,
      pageSize: 20,
      user: null,
      node: null
    }
    var ensureArray = (raw) => {
      if (raw) {
        return Array.isArray(raw) ? raw : [raw]
      }
      return raw
    }
    const data = {
      loading: null,
      defaultFilter: defaultFilter,
      jobsFilter: this.$route.query.jobsFilter || defaultFilter.jobsFilter,
      jobsFilterUser: ensureArray(this.$route.query.user) || defaultFilter.jobsFilterUser,
      jobsFilterNode: ensureArray(this.$route.query.node) || defaultFilter.jobsFilterNode,
      // pageSizeToGo: dealing with element-ui issue,
      // when you choose a large `pageSize`, which may change your current `page`,
      // element-ui will call not only `size-change` but also `current-change`
      // we use pageSizeToGo to eliminate incorrect `current-change` call
      pageSizeToGo: parseInt(this.$route.query.pageSize || defaultFilter.pageSize),
      jobsData: {
        count: 0,
        pageSize: parseInt(this.$route.query.pageSize || defaultFilter.pageSize),
        page: parseInt(this.$route.query.page || defaultFilter.page),
        data: []
      },
      editJobDialog: {
        visible: false,
        title: 'Create Job',
        data: Object.assign({}, defaultJobData),
        disabledFields: {},
        type: 'create'
      },
      repos: [],
      nodes: []
    }
    return data
  },
  mounted: function () {
    this.loadJobs(this.jobsData.page, this.jobsData.pageSize)
    this.$http.get('./api/repos?pageSize=0&repo_only=1').then((resource) => {
      for (var i = 0; i < resource.body.data.length; i++) {
        this.repos.push({ 'value': resource.body.data[i].repo })
      }
    })
    this.$http.get('./api/nodes').then((resource) => {
      this.nodes = resource.body.items
    })
  },
  methods: {
    moment,
    showCreateJob: function () {
      this.checkAuth()
      this.editJobDialog.title = 'Create job'
      this.editJobDialog.disabledFields = {}
      this.editJobDialog.type = 'create'
      this.editJobDialog.visible = true
    },
    showCloneJob: function (index, tableData) {
      this.checkAuth()
      this.editJobDialog.title = 'Clone job'
      this.editJobDialog.disabledFields = {}
      this.editJobDialog.type = 'clone'
      var line = tableData[index]
      this.editJobDialog.data = Object.assign({}, line)
      this.editJobDialog.visible = true
    },
    showEditJob: function (index, tableData) {
      this.checkAuth()
      this.editJobDialog.title = 'Edit job'
      this.editJobDialog.disabledFields = {
        name: true,
        repo: true,
        branch: true,
        // eslint-disable-next-line
        commit_id: true,
      }
      this.editJobDialog.type = 'edit'
      var line = tableData[index]
      if (line.status !== 'ManualStop' && line.status !== 'Completed') {
        for (var field of ['node', 'gpu_num', 'image', 'command', 'volumeMounts']) {
          this.editJobDialog.disabledFields[field] = true
        }
      }
      this.editJobDialog.data = Object.assign({}, line)
      this.editJobDialog.visible = true
    },
    stopJob: function (index, tableData) {
      this.checkAuth()
      var jobName = tableData[index].name
      this.$confirm('Do you really want to stop ' + jobName + '?', 'Stop job', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(() => {
        this.$http.post('./api/job/stop/' + jobName, {}).then((resource) => {
          this.$message({
            type: 'success',
            message: jobName + ' stopped!'
          })
          this.loadJobs(this.jobsData.page)
          this.editJobDialog.visible = false
        })
      }).catch(() => {
        this.$message({
          type: 'info',
          message: 'Cancel.'
        })
      })
    },
    restartJob: function (index, tableData) {
      this.checkAuth()
      var jobName = tableData[index].name
      this.$confirm('Do you really want to Restart ' + jobName + '?', 'Restart job', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(() => {
        this.$http.post('./api/job/restart/' + jobName, {}).then((resource) => {
          this.$message({
            type: 'success',
            message: jobName + ' Restarted!'
          })
          this.loadJobs(this.jobsData.page)
          this.editJobDialog.visible = false
        })
      }).catch(() => {
        this.$message({
          type: 'info',
          message: 'Cancel.'
        })
      })
    },
    startBoard: function (index, tableData) {
      this.checkAuth()
      var line = tableData[index]
      this.$prompt('Please enter logdir. You can use $JOB_NAME, $WORK_DIR, $OUTPUT_DIR', 'TensorBoard', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel'
      }).then((data) => {
        this.$http.post('./api/job/tensorboard/' + line.name, { 'logdir': data.value }).then(() => {
          this.loadJobs(this.jobsData.page)
        })
      }).catch(() => {

      })
    },
    stopBoard: function (index, tableData) {
      this.checkAuth()
      var line = tableData[index]
      this.$http.delete('./api/job/tensorboard/' + line.name).then(() => {
        this.loadJobs(this.jobsData.page)
        this.$message({
          type: 'info',
          message: 'TensorBoard stopped.'
        })
      }).catch((response) => {
        this.loadJobs(this.jobsData.page)
        this.$message.error(response.body)
        console.error(response.body)
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
      this.loading = Loading.service({ target: this.$refs.rootdiv })
      var params = {}
      params['page'] = page
      if (this.jobsFilter === 'Hidden') {
        params['hide'] = '1'
      } else if (this.jobsFilter === 'Fav') {
        params['fav'] = '1'
      } else if (this.jobsFilter === 'Running') {
        params['status'] = '$RunningExtra' // include all non-stop pod, like crashbackoff, pending
        params['hide'] = 'all'
      }
      if (this.jobsFilterUser) {
        params['user'] = this.jobsFilterUser
      }
      if (this.jobsFilterNode) {
        params['node'] = this.jobsFilterNode
      }
      params['pageSize'] = pageSize
      var routerQuery = {
        jobsFilter: this.jobsFilter,
        user: this.jobsFilterUser,
        node: this.jobsFilterNode,
        page: page,
        pageSize: pageSize
      }
      for (var k in routerQuery) {
        if (routerQuery[k] === this.defaultFilter[k]) {
          delete routerQuery[k]
        }
      }
      this.$router.push({ query: routerQuery })
      this.$http.get('./api/jobs', { params: params }).then((resource) => {
        if (this.loading) {
          this.loading.close()
        }
        this.jobsData = resource.body
      })
    },
    onConfirmEdit: function (job) {
      if (this.editJobDialog.type === 'edit') {
        var updateBody = {
          '_id': job._id,
          'comments': job.comments
        }
        if (job.status === 'ManualStop' || job.status === 'Completed') {
          for (var field of ['node', 'gpu_num', 'image', 'command', 'volumeMounts']) {
            updateBody[field] = job[field]
          }
        }
        this.$http.put('./api/jobs', updateBody).then(() => {
          this.loadJobs(this.jobsData.page)
          this.editJobDialog.visible = false
        }).catch((response) => {
          this.$message.error(response.body)
          console.error(response.body)
        })
        return
      }
      this.$http.post('./api/jobs', job).then((resource) => {
        this.loadJobs(1)
        this.editJobDialog.visible = false
      }).catch((response) => {
        this.$message.error(response.body)
        console.error(response.body)
      })
    },
    jobHideChange: function (line, event) {
      this.$http.put('./api/jobs', {
        '_id': line._id,
        'hide': event
      }).then(() => {
        line.hide = event
      }).catch(() => {
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
      this.$http.put('./api/jobs', {
        '_id': line._id,
        'fav': !line.fav
      }).then(() => {
        line.fav = !line.fav
      }).catch(() => {
      })
    },
    jobsFilterChange: function (filter) {
      console.log(filter)
      if (filter.user !== undefined) { // which mean table.filter-change call this function
        if (filter.user.length) {
          this.jobsFilterUser = filter.user
        } else {
          this.jobsFilterUser = null
        }
      }
      if (filter.node !== undefined) {
        if (filter.node.length) {
          this.jobsFilterNode = filter.node
        } else {
          this.jobsFilterNode = null
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
    },
    filterNodes: function () {
      var nodes = []
      for (const node of this.nodes) {
        nodes.push({ text: node.name, value: node.name })
      }
      return nodes
    }
  }
}
</script>
<style lang="scss">
.table-header {
  padding: .5em 0;
  .el-pagination {
    display: inline-block;
  }
  .el-pagination,
  .el-button,
  .el-radio-group {
    vertical-align: middle;;
  }
}
.inline-form-span {
  width: 1em;
  height: 1em;
  float: left;
}
.job-expand-item {
  margin-bottom: 10px;
  overflow: hidden;
  zoom: 1;
  > div {
    margin-left: 100px;
    > pre{
      margin: 0;
      white-space: pre-wrap;
    }
  }
  > label {
    width: 100px;
    float: left;
    text-align: right;
    padding-right: 1em;
    box-sizing: border-box;
  }
  .el-tag+.el-tag {
    margin-left: 1em;
  }
  .el-button {
    padding: 0;
  }
}
.status-stop-wrap {
  display: inline-block;
  width: 32px;
}
.el-table .positive-row {
  background: #e2f0e4;
}
</style>

<template>
  <div>
    <div class="table-header">
      <el-button size="small" type="primary" @click="checkAuth(), createRepoDialog.visible = true">Create Repo</el-button>
      <el-pagination
        layout="prev, pager, next"
        :page-size="reposData.pageSize"
        :total="reposData.total"
        @current-change="loadRepos"
        >
      </el-pagination>
    </div>
    <el-table
      :data="reposData.data"
      style="width: 100%"
      v-loading="reposData.loading">
      <el-table-column
        prop="repo"
        label="repo"
        :show-overflow-tooltip="true">
      </el-table-column>
      <el-table-column label="Action" width="200">
        <template scope="scope">
          <el-button
            size="small"
            type="danger"
            @click="handleDelete(scope.row)">Delete</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog :title="createRepoDialog.title" v-model="createRepoDialog.visible" size="large">
      <el-form ref="form" :model="createRepoDialog.data" label-width="80px">
        <el-form-item label="Repo">
         <el-input v-model="createRepoDialog.data.repo"></el-input>
        </el-form-item>
        <el-form-item label="ssh_key">
         <el-input type="textarea" :rows=3 v-model="createRepoDialog.data.ssh_key"></el-input>
        </el-form-item>
        <el-form-item label="Username">
         <el-input v-model="createRepoDialog.data.username"></el-input>
        </el-form-item>
        <el-form-item label="Password">
         <el-input v-model="createRepoDialog.data.password"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="createRepoDialog.visible = false">取 消</el-button>
        <el-button type="primary" @click="createRepo">确 定</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
export default {
  template: '#tq-repos-template',
  props: {
    checkAuth: Function
  },
  data: function () {
    return {
      reposData: {
        count: 0,
        pageSize: 20,
        page: 1,
        loading: false,
        data: []
      },
      createRepoDialog: {
        visible: false,
        title: 'Create Repo',
        data: {
          repo: '',
          //eslint-disable-next-line
          ssh_key: '', // TODO
          username: '',
          password: ''
        }
      }
    }
  },
  mounted: function () {
    this.loadRepos(1)
  },
  methods: {
    loadRepos: function (page) {
      this.reposData.loading = true
      this.$http.get('/api/repos?page=' + page).then(function (resource) {
        resource.body.loading = false
        this.reposData = resource.body
      })
    },
    createRepo: function () {
      this.$http.post('/api/repos', this.createRepoDialog.data).then(function (resource) {
        this.loadRepos(1)
        this.createRepoDialog.visible = false
      })
    },
    handleDelete (row) {
      this.$confirm('Do you really want to Delete ' + row.repo + '?', 'Delete Repo', {
        confirmButtonText: 'Confirm',
        cancelButtonText: 'Cancel',
        type: 'warning'
      }).then(() => {
        this.$http.delete(`/api/repos/${row._id}`).then(resource => {
          this.loadRepos(1)
        }).catch(resource => {
          this.$message.error(resource.body)
          console.error(resource.body)
        })
      })
    }
  }
}
</script>

<template>
<div>
  <div class="table-header">
    <el-button size="small" type="primary" @click="createRepoDialog.visible = true">Create Repo</el-button>
    <el-pagination layout="prev, pager, next" :page-size="reposData.pageSize" :total="reposData.total" @current-change="loadRepos">
    </el-pagination>
  </div>
  <el-table :data="reposData.data" style="width: 100%" v-loading="reposData.loading">
    <el-table-column prop="repo" label="repo" :show-overflow-tooltip="true">
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
      <el-form-item label="Auth">
        <el-radio-group v-model="createRepoDialog.data.authType">
          <el-radio-button label="ssh_key">SSH-key</el-radio-button>
          <el-radio-button label="https_password">HTTPS password</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="SSH Key" v-if="createRepoDialog.data.authType == 'ssh_key'">
        <el-input type="textarea" :rows="3" v-model="createRepoDialog.sshKey"></el-input>
      </el-form-item>
      <el-form-item label="Username" v-if="createRepoDialog.data.authType == 'https_password'">
        <el-input v-model="createRepoDialog.username"></el-input>
      </el-form-item>
      <el-form-item label="Password" v-if="createRepoDialog.data.authType == 'https_password'">
        <el-input v-model="createRepoDialog.password" type="password"></el-input>
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
        sshKey: '',
        username: '',
        password: '',
        data: {
          repo: '',
          authType: 'ssh_key',
          credential: {}
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
      this.$http.get('./api/repos?page=' + page).then(function (resource) {
        resource.body.loading = false
        this.reposData = resource.body
      })
    },
    createRepo: function () {
      switch (this.createRepoDialog.data.authType) {
        case 'https_password':
          this.createRepoDialog.data.credential = {
            username: this.createRepoDialog.username,
            password: this.createRepoDialog.password
          }
          break
        case 'ssh_key':
          this.createRepoDialog.data.credential = {
            sshKey: this.createRepoDialog.sshKey
          }
      }
      this.$http.post('./api/repos', this.createRepoDialog.data).then(function (resource) {
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
<style>
.el-form-item .el-radio-group {
  vertical-align: middle;
}
</style>
